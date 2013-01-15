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
    container_computedrtypes = ()

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
            return parent.cw_adapt_to('Container').related_container

    @property
    def parent(self):
        if needs_container_parent(self.entity.e_schema):
            parent = self.entity.container_parent
            return parent[0] if parent else None
        rtype, role = first_parent_rtype_role(self.entity.e_schema)
        return self.entity.related(rtype=rtype, role=role, entities=True)[0]


class ContainerClone(EntityAdapter):
    """ allows to clone big sized containers while being relatively fast
    and not too memory hungry
    (This is quite 'optimized' already, hence not always easy to follow.)
    """
    __regid__ = 'Container.clone'

    def _complete_rql(self, etype):
        """ etype -> rql to fetch all instances from the container """
        if hasattr(self.entity, '_complete_rql'):
            warn('container: you should move _complete_rql to an adapter',
                 DeprecationWarning)
            return self.entity._complete_rql(etype)
        return 'Any X WHERE X is %s, X %s C, C eid %%(container)s' % (
            etype, self.entity.container_rtype)

    @cachedproperty
    def _meta_but_fetched(self):
        return set([self.entity.container_rtype,
                    'creation_date', 'modification_date', 'cwuri'])

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
        meta_but_fetched = self._meta_but_fetched
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
            if (rtype in self.entity.clone_rtypes_to_skip
                or not (rschema.final or rschema.inlined)
                or (rschema.meta and not rtype in meta_but_fetched)):
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
        if hasattr(self.entity, '_queryargs'):
            warn('container: you should move _query_args to an adapter',
                 DeprecationWarning)
            qa = self.entity._queryargs()
            if 'case' in qa:
                # rename case -> container
                qa['container'] = qa['case']
                del qa['case']
            return qa
        return {'container': self.orig_container_eid}

    def clonable_rtypes(self, etype):
        eschema = self._cw.vreg.schema[etype]
        for rschema in eschema.subject_relations():
            rtype = rschema.type
            if not (rschema.inlined or rschema.final
                    or rschema.meta or rtype in self.entity.clone_rtypes_to_skip):
                yield rtype

    def clonable_etypes(self):
        for etype in ordered_container_etypes(self._cw.vreg.schema,
                                              self.entity.__regid__,
                                              self.entity.container_rtype,
                                              self.entity.clone_rtypes_to_skip):
            if etype in self.entity.clone_etypes_to_skip:
                continue
            yield etype

    def _etype_clone(self, etype, orig_to_clone):
        # 1/ fetch all <etype> entities in current container
        queryargs = self._queryargs()
        query, fetched_rtypes, inlined_rtypes = self._etype_fetch_rqlst(etype)
        candidates_rset = self._cw.execute(query, queryargs)
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
        self._etype_relink_clones(etype, queryargs, relations, deferred_relations)

        # 4/ handle deferred relations
        self._flush_deferred(deferred_relations)
        return relations

    def _flush_deferred(self, deferred_relations):
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
        clone_rtype = self.entity.clone_rtype_role[0]
        skiprtypes = set((clone_rtype,)).union(self.entity.clone_rtypes_to_skip)
        for rschema in ceschema.subject_relations():
            if rschema.final:
                continue
            rtype = rschema.type
            if rtype in skiprtypes:
                continue
            if rschema.meta and rtype not in self._meta_but_fetched:
                continue
            etype_rqlst = parse(etype_rql).children[0]
            _add_rqlst_restriction(etype_rqlst, rtype)
            linked_rset = self._cw.execute(etype_rqlst, queryargs)
            for ceid, linked_eid in linked_rset:
                if rtype in self._specially_handled_rtypes:
                    deferred_relations.append((rtype, ceid, linked_eid))
                else:
                    relations[rtype].append((ceid, linked_eid))
        self._flush_deferred(deferred_relations)
        return relations

    def container_rtypes_etypes(self):
        etype = self.entity.e_schema.type
        containerclass = self._cw.vreg['etypes'].etype_class(etype)
        rtypes, etypes = container_rtypes_etypes(self._cw.vreg.schema, etype,
                                                 containerclass.container_rtype,
                                                 skiprtypes=containerclass.container_skiprtypes)
        return rtypes, etypes

    def _init_clone_map(self):
        rtype, role = self.entity.clone_rtype_role
        self.orig_container_eid = self.entity.related(rtype, role).rows[0][0]
        return {self.orig_container_eid: self.entity.eid}

    def clone(self):
        """ entry point """
        internal_rtypes, clonable_etypes = self.container_rtypes_etypes()

        orig_to_clone = self._init_clone_map()
        relations = defaultdict(list)
        cloned_etypes = []
        for etype in self.clonable_etypes():
            cloned_etypes.append(etype)
            for rtype, from_to in self._etype_clone(etype, orig_to_clone).iteritems():
                relations[rtype].extend(from_to)

        # the container itself is walked: its subject relations have not yet
        # been collected
        for rtype, from_to in self._container_relink(orig_to_clone).iteritems():
            relations[rtype].extend(from_to)

        uncloned_etypes = set(cloned_etypes) - clonable_etypes
        if uncloned_etypes:
            self.info('etypes %s were not cloned', uncloned_etypes)

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

    @cachedproperty
    def _specially_handled_rtypes(self):
        """ rtypes in this set will not be handled by the default
        cloning algorithm, instead they are accumulated and handled at
        the end to the handle_special_relations method (whose default
        implementation does nothing)
        """
        if hasattr(self.entity, '_specially_handled_rtypes'):
            warn('container: you should move _specially_handled_rtypes '
                 'to an adapter', DeprecationWarning)
            return self.entity._specially_handled_rtypes
        return ()

    def handle_special_relations(self, deferred_relations):
        if hasattr(self.entity, 'handle_special_relations'):
            warn('container: you should move handle_special_relations '
                 'to an adapter', DeprecationWarning)
            self.entity.handle_special_relations(deferred_relations)


class MultiParentProtocol(EntityAdapter):
    __regid__ = 'container.multiple_parents'
    __select__ = yet_unset()

    def possible_parent(self, rtype, eid):
        pass

