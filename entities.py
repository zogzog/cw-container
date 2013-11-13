# copyright 2011-2012 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
from warnings import warn

from logilab.common.decorators import cached, cachedproperty

from rql import parse

from cubicweb.server.ssplanner import READ_ONLY_RTYPES

from cubicweb.schema import VIRTUAL_RTYPES
from cubicweb.entities import AnyEntity
from cubicweb.view import EntityAdapter

from cubes.container.utils import (yet_unset,
                                   ordered_container_etypes,
                                   container_rtypes_etypes,
                                   parent_rschemas,
                                   needs_container_parent,
                                   _add_rqlst_restriction,
                                   _iter_mainvar_relations)

class Container(AnyEntity):
    __abstract__ = True

    # container API
    container_rtype = None
    container_skiprtypes = ()
    container_skipetypes = ()
    container_subcontainers = ()
    compulsory_hooks_categories = ()


@cached
def container_etypes(vreg):
    return set(c.__regid__
               for c, in vreg['etypes'].itervalues()
               if getattr(c, 'container_rtype', False))


@cached
def first_parent_rtype_role(eschema):
    return list(parent_rschemas(eschema))[0]

class ContainerProtocol(EntityAdapter):
    __regid__ = 'Container'
    clone_rtype_role = None

    @property
    def related_container(self):
        if self.entity.e_schema in container_etypes(self._cw.vreg):
            # self.entity is the container itself
            return self.entity
        try:
            ccwetype = self.entity.container_etype
        except AttributeError:
            # that was definitely not a container entity
            return None
        if ccwetype:
            etypes = self._cw.vreg['etypes']
            crtype = etypes.etype_class(ccwetype[0].name).container_rtype
            container = getattr(self.entity, crtype, None)
            if container:
                return container[0]
        # container relation is still unset, let's ask the parent
        parent = self.parent
        if parent:
            container = parent.cw_adapt_to('Container').related_container
            if self.entity.e_schema not in container.container_skipetypes:
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
            etype, self.entity.container_rtype)

    @cachedproperty
    def _no_copy_meta(self):
        # handled unconditionnally by the native source, hence we must not touch them
        # ALSO include cwuri, which is mandatory in cw but maybe should not
        # (see cw#3267139)
        return set(('cw_source', 'cwuri')) | READ_ONLY_RTYPES | VIRTUAL_RTYPES

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
        for etype in ordered_container_etypes(self._cw.vreg.schema,
                                              self.entity.__regid__,
                                              self.entity.container_rtype,
                                              self.rtypes_to_skip,
                                              self.etypes_to_skip,
                                              self.entity.container_subcontainers):
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

    def _etype_create_clones(self, etype, orig_to_clone, candidates_rset,
                             relations, deferred_relations,
                             fetched_rtypes, inlined_rtypes):
        create = self._cw.create_entity
        for row in candidates_rset.rows:
            candidate_eid = row[0]
            attributes = {}
            for rtype, val in zip(fetched_rtypes, row[1:]):
                if val is None:
                    continue
                if rtype in inlined_rtypes:
                    if rtype in self._specially_handled_rtypes:
                        deferred_relations.append((rtype, candidate_eid, val))
                    elif val in orig_to_clone:
                        attributes[rtype] = orig_to_clone[val]
                    else:
                        relations[rtype].append((candidate_eid, val))
                else: # standard attribute
                    attributes[rtype] = val
            # work around cwuri obnoxiousness
            if 'cwuri' not in attributes:
                attributes['cwuri'] = u''
            clone = create(etype, **attributes)
            clone.cw_clear_all_caches()
            orig_to_clone[candidate_eid] = clone.eid

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
        """
        deferred_relations = []
        relations = defaultdict(list)
        queryargs = self._queryargs()
        ceschema = self.entity.e_schema
        etype = ceschema.type
        etype_rql = 'Any X WHERE X is %s, X eid %s' % (
                etype, self.orig_container_eid)
        skiprtypes = set(self.rtypes_to_skip)
        if self.clone_rtype:
            skiprtypes.add(self.clone_rtype)
        for rschema in ceschema.subject_relations():
            if rschema.final:
                continue
            rtype = rschema.type
            if rtype in skiprtypes:
                continue
            if rtype not in VIRTUAL_RTYPES:
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
        etype = self.entity.e_schema.type
        containerclass = self._cw.vreg['etypes'].etype_class(etype)
        rtypes, etypes = container_rtypes_etypes(self._cw.vreg.schema, etype,
                                                 containerclass.container_rtype,
                                                 skiprtypes=containerclass.container_skiprtypes)
        return rtypes, etypes

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

