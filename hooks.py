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
"""cubicweb-container specific hooks and operations"""

from collections import defaultdict

from logilab.common.deprecation import class_deprecated

from cubicweb import ValidationError
from cubicweb.server.hook import Hook, DataOperationMixIn, Operation

from cubes.container.utils import parent_rschemas

def eid_etype(session, eid):
    return session.describe(eid)[0]

def entity_and_parent(session, eidfrom, rtype, eidto, etypefrom, etypeto):
    """ given a triple (eidfrom, rtype, eidto)
    where one of the two eids is the parent of the other,
    compute a return (eid, eidparent)
    """
    crole = session.vreg.schema[rtype].rdef(etypefrom, etypeto).composite
    if crole == 'object':
        return eidfrom, eidto
    else:
        return eidto, eidfrom

def find_valued_parent_rtype(entity):
    for rschema, role in parent_rschemas(entity.e_schema):
        if entity.related(rschema.type, role=role):
            return rschema.type

def _set_container_parent(session, rtype, eid, peid):
    target = session.entity_from_eid(eid)
    if target.container_parent:
        mp_protocol = target.cw_adapt_to('container.multiple_parents')
        if mp_protocol:
            mp_protocol.possible_parent(rtype, peid)
            return
        cparent = target.container_parent[0]
        if cparent.eid == peid:
            session.warning('relinking %s (eid:%s parent:%s)', rtype, eid, peid)
            return
        # this is a replacement: we allow replacing within the same container
        # for the same rtype
        old_rtype = find_valued_parent_rtype(target)
        assert old_rtype
        try:
            icontainer = target.cw_adapt_to('Container')
        except Exception:
            # select ambiguity, only in debug mode
            msg = (session._('%s is already in a container through %s') %
                   (target.e_schema, rtype))
            raise ValidationError(target.eid, {rtype: msg})
        container = icontainer.related_container
        parent = session.entity_from_eid(peid)
        parent_container = parent.cw_adapt_to('Container').related_container
        if (container is not None and parent_container is not None and
                (container.eid != parent_container.eid or old_rtype != rtype)):
            session.warning('%s is already in container %s, cannot go into %s '
                         ' (rtype from: %s, rtype to: %s)',
                         target, parent_container, container, old_rtype, rtype)
            msg = (session._('%s is already in a container through %s') %
                   (target.e_schema, rtype))
            raise ValidationError(target.eid, {rtype: msg})
    target.cw_set(container_parent=peid)


class SetContainerRelation(Hook):
    __regid__ = 'container.set_container_relation'
    __abstract__ = True
    events = ('after_add_relation',)
    category = 'container'
    # __select__ = match_rtype(set_container_relation_rtypes_hook(...))
    # _container_parent_rdefs = container_parent_rdefs(...)
    _container_parent_rdefs = {}

    def __call__(self):
        etypefrom = eid_etype(self._cw, self.eidfrom)
        etypeto = eid_etype(self._cw, self.eidto)
        eid, peid = entity_and_parent(self._cw, self.eidfrom, self.rtype, self.eidto,
                                      etypefrom, etypeto)
        AddContainerRelationOp.get_instance(self._cw).add_data((eid, peid))
        # container_parent handling
        rdefs = self._container_parent_rdefs.get(self.rtype)
        if rdefs and (etypefrom, etypeto) in rdefs:
            _set_container_parent(self._cw, self.rtype, eid, peid)


class SetChildContainerRelation(Hook):
    """Handle pre-existing subgraphs of the container being attached to the
    container so that children of these subgraphs have the container relation
    set."""
    __regid__ = 'container.set_child_container_relation'
    __abstract__ = True
    events = ('after_add_relation',)
    category = 'container'
    # __select__ = match_rtype(container.container_rtype)

    def __call__(self):
        container = self._cw.entity_from_eid(self.eidto)
        peid = self.eidfrom
        etypefrom = eid_etype(self._cw, peid)
        eschema = self._cw.vreg.schema[etypefrom]
        for rschema, targets, role in eschema.relation_definitions():
            if rschema in container.container_config.skiprtypes:
                continue
            rdef = eschema.rdef(rschema, role, takefirst=True)
            if rdef.composite == role:
                if role == 'subject':
                    rql = 'Any C WHERE X %s C, X eid %%(x)s' % rschema
                else:
                    rql = 'Any C WHERE C %s X, X eid %%(x)s' % rschema
                for eid, in self._cw.execute(rql, {'x': peid}):
                    AddContainerRelationOp.get_instance(self._cw).add_data(
                        (eid, peid))


class SetContainerParent(Hook):
    __metaclass__ = class_deprecated
    __deprecation_warning__ = ('[2.2.0] SetContainerParent is deprecated, '
                               'read the upgrade notes')
    __regid__ = 'container.set_container_parent'
    __abstract__ = True
    events = ('before_add_relation',)
    category = 'container'

    def __call__(self):
        etypefrom = eid_etype(self._cw, self.eidfrom)
        etypeto = eid_etype(self._cw, self.eidto)
        eid, peid = entity_and_parent(self._cw, self.eidfrom, self.rtype, self.eidto,
                                      etypefrom, etypeto)
        _set_container_parent(self._cw, self.rtype, eid, peid)


class AddContainerRelationOp(DataOperationMixIn, Operation):
    """ when all relations are set, we set <container> """

    def insert_index(self):
        """ we schedule ourselve ahead of all other operations """
        return 0

    def _container_cwetype_eid(self, container, cwetype_eid_map):
        etype = container.e_schema.type
        if etype in cwetype_eid_map:
            return cwetype_eid_map[etype]
        eid = self.session.execute('CWEType T WHERE T name %(name)s',
                                   {'name': etype}).rows[0][0]
        cwetype_eid_map[etype] = eid
        return eid

    def precommit_event(self):
        cwetype_eid_map = {}
        session = self.session
        container_rtype_rel = defaultdict(list)
        container_etype_rel = []
        for eid, peid in self.get_data():
            parent = session.entity_from_eid(peid)
            cprotocol = parent.cw_adapt_to('Container')
            container = cprotocol.related_container
            if container is None:
                # A subgraph of the container can exist without a container.
                self.warning('Cannot find container related to parent entity %d; '
                             'probably because it is part of a subgraph not yet '
                             'related to its container.' % eid)
                continue
            container_rtype_rel[container.container_config.rtype].append((eid, container.eid))
            container_etype_rel.append((eid, self._container_cwetype_eid(container, cwetype_eid_map)))
        if container_rtype_rel:
            session.add_relations(container_rtype_rel.items())
        if container_etype_rel:
            session.add_relations([('container_etype', container_etype_rel)])


# clone using <clone_relation> Hook & Operation

class CloneContainer(Hook):
    __regid__ = 'container.clone'
    events = ('after_add_relation',)
    #__select__ = None use match_rtype(container_clone_rtype)
    __abstract__ = True
    category = 'container'

    def __call__(self):
        CloneContainerOp.get_instance(self._cw).add_data(self.eidfrom)


class CloneContainerOp(DataOperationMixIn, Operation):

    def prepare_cloned_container(self, session, clone):
        """ give a chance to cleanup cloned container before the process starts
        e.g.: it may already have a workflow state but we want to ensure it has none
        before it is entirely cloned
        """
        pass

    def postcommit_event(self):
        for cloneid in self.get_data():
            with self.session.repo.internal_session() as session:
                cloned = session.entity_from_eid(cloneid)
                cloner = cloned.cw_adapt_to('Container.clone')
                # XXX(syt) why isn't this in the adapter rather than in the
                # operation?
                with session.deny_all_hooks_but(*cloner.compulsory_hooks_categories):
                    self.prepare_cloned_container(session, cloned)
                    cloner.clone()
                    self.finalize_cloned_container(session, cloned)
                    session.commit()

    def finalize_cloned_container(self, session, clone):
        """ give a chance to cleanup cloned container after the cloning
        (can be useful for various hooks)
        """
        pass
