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
from datetime import datetime
from collections import defaultdict
from itertools import izip
from warnings import warn

from logilab.common.decorators import cached, cachedproperty
from logilab.common.deprecation import class_deprecated, deprecated

from rql import parse

from cubicweb import Binary
from cubicweb.server.ssplanner import READ_ONLY_RTYPES
from cubicweb.server.utils import eschema_eid

from cubicweb.schema import VIRTUAL_RTYPES
from cubicweb.entities import AnyEntity
from cubicweb.view import EntityAdapter

from cubes.container import ContainerConfiguration
from cubes.container.utils import (yet_unset,
                                   ordered_container_etypes,
                                   container_rtypes_etypes,
                                   parent_rschemas,
                                   needs_container_parent,
                                   _insertmany,
                                   _add_rqlst_restriction,
                                   _iter_mainvar_relations)


class Container(AnyEntity):
    __metaclass__ = class_deprecated
    __deprecation_warning__ = '[container 2.4] Use ContainerConfiguration'
    __abstract__ = True

    # container API
    container_rtype = None
    container_skiprtypes = ()
    container_skipetypes = ()
    container_subcontainers = ()
    compulsory_hooks_categories = ()

    @classmethod
    def __initialize__(cls, schema):
        super(Container, cls).__initialize__(schema)
        cls.container_config = ContainerConfiguration(
            cls.__regid__, cls.container_rtype,
            skiprtypes=cls.container_skiprtypes,
            skipetypes=cls.container_skipetypes,
            subcontainers=cls.container_subcontainers,
            compulsory_hooks_categories=cls.compulsory_hooks_categories)


@cached
def container_etypes(vreg):
    result = []
    for regid in vreg['etypes']:
        eclass = vreg['etypes'].etype_class(regid)
        if hasattr(eclass, 'container_config'):
            result.append(regid)
    return frozenset(result)

@cached
def first_parent_rtype_role(eschema):
    return list(parent_rschemas(eschema))[0]

class ContainerProtocol(EntityAdapter):
    __regid__ = 'Container'
    clone_rtype_role = None

    @property
    @deprecated('[container 2.4] Use ContainerConfiguration')
    def container_rtype(self):
        # Pre ContainerConfiguration API. Otherwise, the `container_rtype`
        # attribute is set upon class generation in `build_container_protocol`
        # method.
        try:
            ccwetype = self.entity.container_etype
        except AttributeError:
            # that was definitely not a container entity
            return None
        if ccwetype:
            etypes = self._cw.vreg['etypes']
            return etypes.etype_class(ccwetype[0].name).container_rtype

    @property
    def related_container(self):
        if self.entity.e_schema in container_etypes(self._cw.vreg):
            # self.entity is the container itself
            return self.entity
        if self.container_rtype is not None:
            container = getattr(self.entity, self.container_rtype, None)
            if container:
                return container[0]
        # container relation is still unset, let's ask the parent
        parent = self.parent
        if parent:
            container = parent.cw_adapt_to('Container').related_container
            if container is None:
                return
            if (self.entity.e_schema not in
                    container.container_config.skipetypes):
                return container

    @property
    def parent(self):
        if needs_container_parent(self.entity.e_schema):
            parent = self.entity.container_parent
            return parent[0] if parent else None
        try:
            rtype, role = first_parent_rtype_role(self.entity.e_schema)
        except IndexError:
            # that was likely a non-container entity
            # this can happen since this adapter is selectable
            # for any entity type
            return None
        parent = self.entity.related(rtype=rtype, role=role, entities=True)
        if parent:
            return parent[0]


class ContainerClone(EntityAdapter):
    """ allows to clone big sized containers while being relatively fast
    and not too memory hungry
    (This is quite 'optimized' already, hence not always easy to follow.)
    """
    __abstract__ = True
    __regid__ = 'Container.clone'
    rtypes_to_skip = set()
    etypes_to_skip = set()

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

    def clone(self, original=None):
        """ entry point

        At the end, self.entity is the fully cloned container.
        """
        self.orig_container_eid = self._origin_eid(original)

        orig_to_clone = {self.orig_container_eid: self.entity.eid}
        relations = defaultdict(list)
        self._clone(orig_to_clone, relations)

    def _clone(self, orig_to_clone, relations, toplevel=True):
        self.info('started cloning %s (toplevel=%s)', self.entity.e_schema, toplevel)
        cloned_etypes = []
        subcontainers = set()
        internal_rtypes, clonable_etypes = self.container_rtypes_etypes()

        for etype in self.clonable_etypes():
            if etype in container_etypes(self._cw.vreg):
                # We will delegate much of the job to the container
                # adapter itself. The sub-container however will be
                # handled like another clonable entity.
                self.info('%s is a container etype scheduled for delegated cloning', etype)
                subcontainers.add(etype)
            cloned_etypes.append(etype)
            for rtype, from_to in self._etype_clone(etype, orig_to_clone).iteritems():
                relations[rtype].extend(from_to)

        uncloned_etypes = set(cloned_etypes) - clonable_etypes
        if uncloned_etypes:
            self.info('etypes %s were not cloned', uncloned_etypes)

        for cetype in subcontainers:
            self._delegate_clone_to_subcontainer(cetype, orig_to_clone, relations)

        if not toplevel:
            self.info('sub-clone terminated, resuming to parent')
            return

        # the top container itself is walked: its subject relations have not yet
        # been collected
        for rtype, from_to in self._container_relink(orig_to_clone).iteritems():
            relations[rtype].extend(from_to)


        # let's flush all collected relations
        self.info('linking (%d relations)', len(relations))
        for rtype, eids in relations.iteritems():
            self.info('%s linking %s' %
                      ('internal' if rtype in internal_rtypes else 'external', rtype))
            subj_obj = []
            for subj, obj in eids:
                subj = orig_to_clone[subj]
                if obj in orig_to_clone:
                    # internal relinking, else it is a link
                    # between internal and external nodes
                    obj = orig_to_clone[obj]
                subj_obj.append((subj, obj))
            self._cw.add_relations([(rtype, subj_obj)])

    def _delegate_clone_to_subcontainer(self, cetype, orig_to_clone, relations):
        self.info('delegated cloning for %s', cetype)
        query = self._complete_rql(cetype)
        candidates_rset = self._cw.execute(query, self._queryargs())
        for candidate in candidates_rset.entities():
            # fetch the container clone
            cclone = self._cw.entity_from_eid(orig_to_clone[candidate.eid])
            cloner = cclone.cw_adapt_to('Container.clone')
            cloner.orig_container_eid = cloner._origin_eid(candidate.eid)
            # the orig-clone mapping and relations will be augmented
            # by the delegated clone
            cloner._clone(orig_to_clone, relations, toplevel=False)
            cloner._container_relink(orig_to_clone)

    @cachedproperty
    def clone_rtype(self):
        """ returns the <clone> rtype if it exists
        (it should be defined as a .clone_rtype_role 2-uple) """
        try:
            return self.clone_rtype_role[0]
        except (AttributeError, IndexError):
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
                rtype, role = self.clone_rtype_role
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
            etype, self.entity.container_config.rtype)

    @cachedproperty
    def _no_copy_meta(self):
        # include cwuri, which is mandatory in cw but maybe should not
        # (see cw#3267139)
        return set(('cwuri',)) | READ_ONLY_RTYPES | VIRTUAL_RTYPES

    def _etype_fetch_rqlst(self, etype):
        """ returns an rqlst ready to be executed, plus a sequence of
        all attributes or inlined rtypes that will be fetched by the rql,
        plus a set of the inlined rtypes
        """
        base_rql = self._complete_rql(etype)
        # modify base_rql to fetch all attributes / inlined rtypes
        rqlst = parse(base_rql).children[0]
        # a dict from rtype to rql variable
        already_used_rtypes = dict(_iter_mainvar_relations(rqlst))
        # running without metadata hooks: we must handle some rtypes here
        # we also will loose: is_instance_of, created_by, owned_by
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

    def clonable_etypes(self):
        for etype in ordered_container_etypes(
                self._cw.vreg.schema,
                self.entity.__regid__,
                self.entity.container_config.rtype,
                self.rtypes_to_skip,
                self.etypes_to_skip,
                self.entity.container_config.subcontainers):
            yield etype

    def _etype_clone(self, etype, orig_to_clone):
        # 1/ fetch all <etype> entities in current container
        query, fetched_rtypes, inlined_rtypes = self._etype_fetch_rqlst(etype)
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

    def _reserve_eids(self, qty):
        """ not fast enough (yet) """
        source = self._cw.repo.sources_by_uri['system']
        for _x in range(qty):
            yield source.create_eid(self._cw)

    def _fast_create_entities(self, etype, entities, orig_to_clone):
        eschema = self._cw.vreg.schema[etype]
        etypeid = eschema_eid(self._cw, eschema)
        ancestorseid = [etypeid] + [eschema_eid(self._cw, aschema)
                                    for aschema in eschema.ancestors()]
        eids = self._reserve_eids(len(entities))
        metadata = []
        isrelation = []
        isinstanceof = []
        now = datetime.utcnow()
        for attributes, neweid in izip(entities, eids):
            oldeid = attributes['eid']
            orig_to_clone[oldeid] = attributes['eid'] = neweid
            metadata.append({'type': etype, 'eid': neweid,
                             'source': 'system', 'asource': 'system',
                             'mtime': now})
            isrelation.append({'eid_from': neweid, 'eid_to': etypeid})
            for ancestor in ancestorseid:
                isinstanceof.append({'eid_from': neweid, 'eid_to': ancestor})

        # insert entities
        _insertmany(self._cw, etype, entities, prefix='cw_')
        # insert metadata
        _insertmany(self._cw, 'entities', metadata)
        _insertmany(self._cw, 'is_relation', isrelation)
        _insertmany(self._cw, 'is_instance_of_relation', isinstanceof)

    def _etype_create_clones(self, etype, orig_to_clone, candidates_rset,
                             relations, deferred_relations,
                             fetched_rtypes, inlined_rtypes):
        clonable_rtypes = set(self.clonable_rtypes(etype))
        entities = []
        for row in candidates_rset.rows:
            candidate_eid = row[0]
            attributes = {'eid': candidate_eid, 'cwuri': u''}
            for rtype, val in zip(fetched_rtypes, row[1:]):
                # even if val is None, we take it
                if rtype in inlined_rtypes:
                    if rtype in self._specially_handled_rtypes:
                        deferred_relations.append((rtype, candidate_eid, val))
                    elif val in orig_to_clone:
                        attributes[rtype] = orig_to_clone[val]
                    elif rtype not in clonable_rtypes:
                        if rtype not in self.entity.container_config.skiprtypes:
                            attributes[rtype] = val
                    else:
                        # this will be costly
                        relations[rtype].append((candidate_eid, val))
                else: # standard attribute
                    if isinstance(val, Binary):
                        val = buffer(val.getvalue())
                    attributes[rtype] = val
            entities.append(attributes)
        self._fast_create_entities(etype, entities, orig_to_clone)

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

    def container_rtypes_etypes(self):
        config = self.entity.container_config
        return container_rtypes_etypes(self._cw.vreg.schema,
                                       self.entity.cw_etype, config.rtype,
                                       skiprtypes=config.skiprtypes)

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
    __select__ = yet_unset()

    def possible_parent(self, rtype, eid):
        pass

