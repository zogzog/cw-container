# copyright 2011-2014 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr -- mailto:contact@logilab.fr
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 2.1 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program. If not, see <http://www.gnu.org/licenses/>.

"""cubicweb-container entity's classes"""
from collections import defaultdict
from itertools import chain
from warnings import warn

from logilab.common.decorators import cached, cachedproperty
from logilab.common.deprecation import class_deprecated

from rql import parse

from cubicweb import neg_role, onevent
from cubicweb.__pkginfo__ import numversion
from cubicweb.server.ssplanner import READ_ONLY_RTYPES

from cubicweb.schema import VIRTUAL_RTYPES
from cubicweb.entities import AnyEntity
from cubicweb.view import EntityAdapter

from cubes.fastimport.entities import FlushController

from cubes.container import config

from cubes.container.utils import (parent_rdefs,
                                   parent_rschemas,
                                   needs_container_parent,
                                   _add_rqlst_restriction,
                                   _iter_mainvar_relations)


class Container(AnyEntity):
    __abstract__ = True
    __metaclass__ = class_deprecated
    __deprecation_warning__ = ('[container 2.4] '
                               'use cubes.container.config.Container instead')

    # container API
    container_rtype = None
    container_skiprtypes = ()
    container_skipetypes = ()
    container_subcontainers = ()
    clone_rtype_role = None
    compulsory_hooks_categories = ()

    @classmethod
    def __initialize__(cls, schema):
        super(Container, cls).__initialize__(schema)
        if cls.cw_etype in config.Container.all_etypes():
            warn('%r container etype is already defined, skipping bw compat handler'
                 % cls.cw_etype)
            return
        cls.container_config = config.Container(
            cls.cw_etype,
            cls.container_rtype,
            skiprtypes=cls.container_skiprtypes,
            skipetypes=cls.container_skipetypes,
            subcontainers=cls.container_subcontainers,
            clone_rtype_role=cls.clone_rtype_role,
            compulsory_hooks_categories=cls.compulsory_hooks_categories)


@cached
def container_etypes(vreg):
    warn('[container 2.4] container_etype is replaced '
         'by config.Container.all()')
    return config.Container.all_etypes()

@cached
def first_parent_rtype_role(eschema):
    warn('[container 2.4] first_parent_rtype_role is replaced '
         'by first_parent_rdef')
    return list(parent_rschemas(eschema))[0]

notcw319 = numversion[:2] < (3, 19)

@cached
def first_parent_rdef(eschema):
    return parent_rdefs(eschema).next()

class ContainerProtocol(EntityAdapter):
    __regid__ = 'Container'
    __abstract__ = True

    @property
    def related_container(self):
        if self.entity.e_schema in config.Container.all_etypes():
            # self.entity is the container itself
            return self.entity
        try:
            ccwetype = self.entity.container_etype
        except AttributeError:
            # that was definitely not a container entity
            return None

        if ccwetype:
            crtype = config.Container.by_etype(ccwetype[0].name).crtype
            container = self.entity.related(rtype=crtype, role='subject', entities=True)
            if container:
                return container[0]

        # container relation is still unset, let's ask the parent
        parent = self.parent
        if parent:
            container = parent.cw_adapt_to('Container').related_container
            if container is None:
                return
            if self.entity.e_schema not in config.Container.by_etype(container.cw_etype).skipetypes:
                return container

    @property
    def parent(self):
        if needs_container_parent(self.entity.e_schema):
            parent = self.entity.container_parent
            return parent[0] if parent else None
        try:
            rdef = first_parent_rdef(self.entity.e_schema)
            rtype, role = rdef.rtype.type, neg_role(rdef.composite)
        except StopIteration:
            self.debug('ContainerProtocol.parent stopped on %s', self.entity)
            return None
        parent = self.entity.related(rtype=rtype, role=role, entities=True)
        if parent:
            return parent[0]


class ErrorHandler(object):
    def append(self, exception):
        raise exception


class ContainerClone(EntityAdapter):
    """ allows to clone big sized containers while being relatively fast
    and not too memory hungry
    (This is quite 'optimized' already, hence not always easy to follow.)
    """
    __abstract__ = True
    __regid__ = 'Container.clone'
    rtypes_to_skip = set()
    etypes_to_skip = set()
    nesting = 0

    def __init__(self, *args, **kwargs):
        super(ContainerClone, self).__init__(*args, **kwargs)
        self.controller = FlushController(self._cw)
        # since we're doing a clone, we will have the cw_source_relation
        self.controller.handle_cw_source_relation = False

    @cachedproperty
    def config(self):
        return config.Container.by_etype(self.entity.cw_etype)

    @property
    def compulsory_hooks_categories(self):
        return self.config.compulsory_hooks_categories

    # These two unimplemented properties are bw compat
    # to drive users from entity.clone_(e/r)types_to_skip
    # to adapter.(e/r)types_to_skip
    @cachedproperty
    def clone_etypes_to_skip(self):
        raise NotImplementedError

    @cachedproperty
    def clone_rtypes_to_skip(self):
        raise NotImplementedError
    # /bw compat

    # When debugging, uncommenting this may help quite a bit
    # def info(self, msg, *args):
    #     print ('.' * self.nesting) + msg % args

    def clone(self, original=None):
        """ entry point

        At the end, self.entity is the fully cloned container.
        """
        self.orig_container_eid = self._origin_eid(original)
        orig_to_clone = {self.orig_container_eid: self.entity.eid}
        relations = defaultdict(list)
        self._inner_clone(orig_to_clone, relations, 0)

        # the top container itself is walked: its subject relations have not yet
        # been collected
        for rtype, from_to in self._container_relink(orig_to_clone).iteritems():
            relations[rtype].extend(from_to)

        # let's flush all collected relations
        self.info('linking (%d relations)', len(relations))
        session = self._cw
        ecache = self._cw.transaction_data.get('ecache', {})
        internal_rtypes = set(rdef.rtype.type
                              for rdef in self.config.inner_rdefs)
        internal_rtypes.add('container_parent')
        for rtype, eids in relations.iteritems():
            self.info('%s linking %s (%s elements)' %
                      ('internal' if rtype in internal_rtypes else 'external',
                       rtype, len(eids)))
            rschema = session.vreg.schema[rtype]
            subj_obj = []
            inlined_subj_obj = []
            for subj, obj in eids:
                newsubj = orig_to_clone[subj]
                if newsubj == self.entity.eid:
                    if rtype == 'cw_source':
                        continue
                if obj in orig_to_clone:
                    # internal relinking, else it is a link
                    # between internal and external nodes
                    obj = orig_to_clone[obj]

                # eids -> entities, for .insert_relations (real relations)
                if not rschema.inlined:
                    subjentity = ecache.get(newsubj)
                    if subjentity is None:
                        subjentity = session.entity_from_eid(newsubj)
                    objentity = ecache.get(obj)
                    if objentity is None:
                        objentity = session.entity_from_eid(obj)
                    subj_obj.append((subjentity, objentity))
                else:
                    inlined_subj_obj.append((newsubj, obj))

            if rschema.inlined:
                # inlined_subj_obj is a list of eid tuples
                if inlined_subj_obj:
                    self._cw.add_relations([(rtype, inlined_subj_obj)])
            else:
                # subj_obj is a list of entity tuples
                if subj_obj:
                    self.controller.insert_relations(rtype, subj_obj)

        errors = ErrorHandler()
        self.controller.run_deferred_hooks(errors)

    def _inner_clone(self, orig_to_clone, relations, nesting):
        self.nesting = nesting
        toplevel = not nesting
        self.info('started cloning into %s (toplevel=%s)', self.entity.dc_title(), toplevel)
        if not toplevel:
            self.nesting += 1
        self.info('%s -> %s', self.orig_container_eid, self.entity.eid)
        cloned_etypes = []
        subcontainers = self.config.subcontainers
        clonable_etypes = self.config.etypes

        clonable_etypes = list(self.clonable_etypes())
        for etype in clonable_etypes:
            cloned_etypes.append(etype)
            for rtype, from_to in self._etype_clone(etype, orig_to_clone).iteritems():
                relations[rtype].extend(from_to)

        uncloned_etypes = set(cloned_etypes) - set(clonable_etypes)
        if uncloned_etypes:
            self.info('etypes %s were not cloned', uncloned_etypes)

        for cetype in subcontainers:
            self._delegate_clone_to_subcontainer(cetype, orig_to_clone, relations)


    def _delegate_clone_to_subcontainer(self, cetype, orig_to_clone, relations):
        self.info('delegated cloning for %s', cetype)
        # get entities of type cetype except the original
        query = self._complete_rql(cetype) + ', NOT X eid %s' % self.orig_container_eid
        candidates_rset = self._cw.execute(query, self._queryargs())
        for candidate in candidates_rset.entities():
            # fetch the container clone
            # NOTE: at this point a top-level clone has no <crtype> set yet
            #       but this subcontainer has been cloned and its relations
            #       prepared
            cclone = self._cw.entity_from_eid(orig_to_clone[candidate.eid])
            assert getattr(cclone, self.config.crtype)[0].eid == self.entity.eid
            cloner = cclone.cw_adapt_to('Container.clone')
            cloner.orig_container_eid = cloner._origin_eid(candidate.eid)
            # the orig-clone mapping and relations will be augmented
            # by the delegated clone
            cloner._inner_clone(orig_to_clone, relations, nesting=self.nesting+1)
            cloner._container_relink(orig_to_clone)

    @cachedproperty
    def clone_rtype(self):
        """ returns the <clone> rtype if it exists
        (it should be defined as a .clone_rtype_role 2-uple) """
        try:
            return self.config.clone_rtype_role[0]
        except (TypeError, IndexError):
            return None

    def _origin_eid(self, original):
        """ computes the original container eid using
        several methods

        To get the original container:
        * either we are given the eid of the original container,
        * or the .clone_rtype_role attribute is a tuple
        """
        if original:
            if not isinstance(original, int):
                raise TypeError('.clone original should be an eid')
            return original
        else:
            if self.clone_rtype:
                rtype, role = self.config.clone_rtype_role
                return self.entity.related(rtype, role).rows[0][0]
            else:
                raise TypeError('.clone wants the original or a relation to the original')


    def _complete_rql(self, etype):
        """ etype -> rql to fetch all instances from the container """
        if hasattr(self.entity, '_complete_rql'):
            warn('container: you should move _complete_rql to an adapter',
                 DeprecationWarning)
            return self.entity._complete_rql(etype)
        return 'Any X WHERE X is %s, X %s C, C eid %%(container)s' % (
            etype, self.config.crtype)

    @cachedproperty
    def _no_copy_meta(self):
        # include cwuri, which is mandatory in cw but maybe should not
        # (see cw#3267139)
        return (READ_ONLY_RTYPES |
                VIRTUAL_RTYPES |
                # handled by insert_entities
                set(('cwuri', 'created_by', 'owned_by')))

    def _etype_fetch_rqlst(self, etype, completefragment=''):
        """ returns an rqlst ready to be executed, plus a sequence of
        all attributes or inlined rtypes that will be fetched by the rql,
        plus a set of the inlined rtypes
        """
        base_rql = self._complete_rql(etype) + completefragment
        # modify base_rql to fetch all attributes / inlined rtypes
        rqlst = parse(base_rql).children[0]
        # a dict from rtype to rql variable
        already_used_rtypes = dict(_iter_mainvar_relations(rqlst))
        # running without metadata hooks: we must handle some rtypes here
        # we also will loose: is_instance_of, cwuri, has_text, eid, is, identity
        no_copy_meta = self._no_copy_meta
        # keep an ordered-list of selected rtypes
        fetched_rtypes = []
        inlined_rtypes = set()
        # NOTE: we don't use entity_class.fetch_rqlst() because:
        #  - fetch_rqlst() needs user to check some read permissions (we
        #    don't need this and it even might fail because fetch_rqlst()
        #    is totally unaware of local perms)
        #  - fetch_rqlst() recurses on target etypes: we don't want this
        for rschema in self._cw.vreg.schema[etype].subject_relations():
            rtype = rschema.type
            if rtype in self.rtypes_to_skip or rtype in VIRTUAL_RTYPES:
                continue
            if rschema.meta and rtype in no_copy_meta:
                continue
            if not rschema.final and not rschema.inlined:
                continue
            fetched_rtypes.append(rtype)
            if rschema.inlined:
                inlined_rtypes.add(rtype)
            # check if this rtype is already used in base_rql's restrictions
            # in which case the only thing to do is to select corresponding var
            if rtype in already_used_rtypes:
                rqlst.append_selected(already_used_rtypes[rtype])
            else:
                # otherwise, add a new restriction and select the new var
                _add_rqlst_restriction(rqlst, rtype, optional=rschema.inlined)
        return rqlst, fetched_rtypes, inlined_rtypes

    def _queryargs(self):
        return {'container': self.orig_container_eid}

    def clonable_rtypes(self, etype):
        eschema = self._cw.vreg.schema[etype]
        no_copy_metas = self._no_copy_meta
        for rschema in eschema.subject_relations():
            rtype = rschema.type
            if not (rschema.inlined or rschema.final
                    or (rschema.meta and rtype in no_copy_metas)
                    or rtype in self.rtypes_to_skip):
                yield rtype

    @cachedproperty
    def _ordered_etypes(self):
        return list(self.clonable_etypes())

    def clonable_etypes(self):
        cconf = self.config
        # more skiprtypes must be deprecated
        # skiprtypes = set(cconf.skiprtypes) | set(self.rtypes_to_skip)
        skipetypes = set(cconf.skipetypes) | set(self.etypes_to_skip)
        for etype in cconf.ordered_etypes:
            if etype not in skipetypes:
                yield etype

    def _etype_clone(self, etype, orig_to_clone):
        # 0/ guard against cloning again the container itself
        guard = ''
        if etype == self.entity.cw_etype:
            eids = (str(x) for x in (self.orig_container_eid, self.entity.eid))
            guard = ', NOT X eid IN (%s)' % ','.join(eids)
        # 1/ fetch all <etype> entities in current container
        query, fetched_rtypes, inlined_rtypes = self._etype_fetch_rqlst(etype, guard)
        candidates_rset = self._cw.execute(query, self._queryargs())
        if not candidates_rset:
            self.info('nothing to be cloned for %s', etype)
            return {}

        self.info('cloning %d %s BOs', len(candidates_rset.rows), etype)

        relations = defaultdict(list)
        deferred_relations = []

        # 2/ clone attributes / inlined relations
        self._etype_create_clones(etype, orig_to_clone, candidates_rset,
                                  relations, deferred_relations,
                                  fetched_rtypes, inlined_rtypes)

        # 3/ clone standard (i.e non-inlined) relations
        self._etype_relink_clones(etype, self._queryargs(), relations, deferred_relations)

        # 4/ handle deferred relations
        self._flush_deferred(deferred_relations, orig_to_clone)
        return relations

    def _flush_deferred(self, deferred_relations, orig_to_clone):
        if len(deferred_relations):
            self.info('relinking deferred (%d relations)', len(deferred_relations))
            self.handle_special_relations((rtype, orig_to_clone[orig], linked)
                                          for rtype, orig, linked in deferred_relations)

    def preprocess_attributes(self, etype, oldeid, attributes):
        pass

    def _crosses_border(self, etype, rtype):
        """ Tells whether the (etype, rtype, *) relation
        has ALL its targets outside of the container """
        if rtype == 'container_parent':
            # it is technically possible that it crosses the border
            # but a container_parent, by design, is always an inner
            # container relation
            return False
        schema = self._cw.vreg.schema
        etypes = set(self._ordered_etypes)
        etypes.add(self.entity.cw_etype)
        return all(target not in etypes
                   for target in schema[rtype].targets(etype))

    def _already_cloned(self, etype, rtype):
        """ Tells whether all targets in the (etype, rtype, TARGET)
        relation can have been already cloned """
        # a shortcut for the container relation
        if rtype == self.config.crtype:
            return True
        schema = self._cw.vreg.schema
        ordered_etypes = self._ordered_etypes
        try:
            return all(ordered_etypes.index(etype) > ordered_etypes.index(target)
                       for target in schema[rtype].targets(etype))
        except ValueError:
            # some target is not clonable
            return False

    def _etype_create_clones(self, etype, orig_to_clone, candidates_rset,
                             relations, deferred_relations,
                             fetched_rtypes, inlined_rtypes):
        entities = []
        # detect inlined rtypes that may be already cloned
        inlined_rtypes_already_cloned = set()
        # detect inlined rtypes that have at least one
        # out-of-container target
        inlined_rtypes_crossing_border = set()

        for rtype in fetched_rtypes:
            if rtype in inlined_rtypes:
                if self._crosses_border(etype, rtype):
                    inlined_rtypes_crossing_border.add(rtype)
                elif self._already_cloned(etype, rtype):
                    inlined_rtypes_already_cloned.add(rtype)

        # Unfortunately, the above classification still can miss
        # opportunities, because the static analysis lacks relevant
        # information.
        # Hence we peek the first rset row to determine if an inlined
        # relation has been cloned, and if by chance it is valued
        # and appears to have a clone, we just avoided to send an inlined
        # relation to .add_relations (which performs horribly).
        iterrows = iter(candidates_rset.rows)
        firstrow = iterrows.next()
        for rtype, val in zip(fetched_rtypes, firstrow[1:]):
            if rtype in inlined_rtypes:
                if rtype in inlined_rtypes_crossing_border:
                    continue
                if val in orig_to_clone:
                    if rtype not in inlined_rtypes_crossing_border:
                        inlined_rtypes_already_cloned.add(rtype)

        # Let's gather some real-life info
        self.info('Optimized inlined rtypes for %s', etype)
        self.info('crossing border (no need to wait for a clone): %s',
                  sorted(inlined_rtypes_crossing_border))
        self.info('already cloned: %s',
                  sorted(inlined_rtypes_already_cloned))
        self.info('unoptimisable: %s', sorted(inlined_rtypes -
                                              (inlined_rtypes_already_cloned |
                                               inlined_rtypes_crossing_border)))

        for row in chain([firstrow], iterrows):
            oldeid = row[0]
            attributes = {}
            for rtype, val in zip(fetched_rtypes, row[1:]):

                if rtype in inlined_rtypes:
                    # We handle these carefully to ensure the following invariant:
                    # either an rtype is handled in attributes or in relation
                    # but this is not a value-dependant decision
                    # (because insertmany is a bit rigid).
                    # Hence, even if val is None, we take it
                    if rtype in self._specially_handled_rtypes:
                        deferred_relations.append((rtype, oldeid, val))
                        continue

                    if rtype in inlined_rtypes_already_cloned:
                        # there can be Nones here
                        if val is not None:
                            assert val in orig_to_clone
                        attributes[rtype] = orig_to_clone.get(val)
                        continue

                    if rtype in inlined_rtypes_crossing_border:
                        # feed it right away
                        attributes[rtype] = val
                        continue

                    # deferred to relations (or nothing if None)
                    if val is not None:
                        relations[rtype].append((oldeid, val))
                    continue

                # standard attribute
                attributes[rtype] = val

            self.preprocess_attributes(etype, oldeid, attributes)
            entities.append((attributes, oldeid))

        def complete_orig_to_clone(entity, _attrs, oldeid):
            """ callback when a new eid has been produced """
            orig_to_clone[oldeid] = entity.eid
        self.controller.insert_entities(etype, entities, complete_orig_to_clone)

    def _etype_relink_clones(self, etype, queryargs, relations, deferred_relations):
        etype_rql = self._complete_rql(etype)
        for rtype in self.clonable_rtypes(etype):
            self.info('  rtype %s', rtype)
            # NOTE: use rqlst.save() / rqlst.recover() ?
            etype_rqlst = parse(etype_rql).children[0]
            # here, we've got something like: Any X WHERE X <container> C, ...
            _add_rqlst_restriction(etype_rqlst, rtype)
            # now, we've got something like: Any X,Y WHERE X <container> C, ..., X <rtype> Y
            linked_rset = self._cw.execute(etype_rqlst, queryargs)
            for ceid, linked_eid in linked_rset:
                if rtype in self._specially_handled_rtypes:
                    deferred_relations.append((rtype, ceid, linked_eid))
                else:
                    relations[rtype].append((ceid, linked_eid))

    def _container_relink(self, orig_to_clone):
        """ handle subject relations of the container - this is
        handled specially because attributes have already been set

        we partition subject relations in two sets:
        * those that are already set (typically .owned_by, .created_by, ...)
        * those that must yet be cloned
        """
        deferred_relations = []
        relations = defaultdict(list)
        queryargs = self._queryargs()
        clone = self.entity
        etype = clone.e_schema.type
        etype_rql = 'Any X WHERE X is %s, X eid %s' % (
                etype, self.orig_container_eid)
        skiprtypes = set(self.rtypes_to_skip)
        if self.clone_rtype:
            skiprtypes.add(self.clone_rtype)
        clone_subject_relations = set(rschema.type
                                      for rschema in clone.e_schema.subject_relations()
                                      if not rschema.final)
        for rtype in self.clonable_rtypes(etype):
            if rtype in clone_subject_relations:
                if self._cw.execute('Any Y LIMIT 1 WHERE X eid %%(clone)s, X %(rtype)s Y'
                                    % {'rtype': rtype}, {'clone': clone.eid}):
                    continue
            etype_rqlst = parse(etype_rql).children[0]
            _add_rqlst_restriction(etype_rqlst, rtype)
            linked_rset = self._cw.execute(etype_rqlst, queryargs)
            for ceid, linked_eid in linked_rset:
                if rtype in self._specially_handled_rtypes:
                    deferred_relations.append((rtype, ceid, linked_eid))
                else:
                    relations[rtype].append((ceid, linked_eid))
        self._flush_deferred(deferred_relations, orig_to_clone)
        return relations

    @cachedproperty
    def _specially_handled_rtypes(self):
        """ rtypes in this set will not be handled by the default
        cloning algorithm, instead they are accumulated and handled at
        the end to the handle_special_relations method (whose default
        implementation does nothing)
        """
        return ()

    def handle_special_relations(self, deferred_relations):
        pass



class MultiParentProtocol(EntityAdapter):
    __regid__ = 'container.multiple_parents'
    __abstract__ = True

    def possible_parent(self, rtype, eid):
        pass


def registration_callback(vreg):
    vreg.register_all(globals().values(), __name__)

    @onevent('after-registry-reload')
    def register_adapter():
        from cubes.container import config
        for adapter in config.Container.container_adapters():
            if adapter.__regid__ not in vreg[adapter.__registry__]:
                vreg.register(adapter)
