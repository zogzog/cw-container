# copyright 2011 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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

from cubicweb import ValidationError
from cubicweb.server.hook import Hook, DataOperationMixIn, Operation, match_rtype

from cubes.container.utils import yet_unset, parent_rschemas

ALL_CONTAINER_RTYPES = set()
ALL_CONTAINER_ETYPES = set()


class SetContainerRelation(Hook):
    __regid__ = 'container.set_container_relation'
    __select__ = Hook.__select__ & match_rtype('container_parent')
    events = ('after_add_relation',)
    category = 'container'

    def __call__(self):
        AddContainerRelationOp.get_instance(self._cw).add_data((self.eidfrom, self.eidto))

def find_valued_parent_rtype(entity):
    for rschema in parent_rschemas(entity.e_schema):
        if entity.related(rschema.type):
            return rschema.type

class SetContainerParent(Hook):
    __regid__ = 'container.set_container_parent'
    __select__ = yet_unset()
    events = ('before_add_relation',)
    category = 'container'

    def __call__(self):
        req = self._cw
        schema = req.vreg.schema
        subjetype = req.describe(self.eidfrom)[0]
        objetype = req.describe(self.eidto)[0]
        crole = schema[self.rtype].rdef(subjetype, objetype).composite
        if crole == 'object':
            eeid, peid = self.eidfrom, self.eidto
        else:
            eeid, peid = self.eidto, self.eidfrom
        target = req.entity_from_eid(eeid)
        if target.container_parent:
            mp_protocol = target.cw_adapt_to('container.multiple_parents')
            if mp_protocol:
                mp_protocol.possible_parent(self.rtype, peid)
                return
            cparent = target.container_parent[0]
            if cparent.eid == peid:
                self.warning('relinking %s %s %s', self.eidfrom, self.rtype, self.eidto)
                return
            # this is a replacement: we allow replacing within the same container
            #                        for the same rtype
            old_rtype = find_valued_parent_rtype(target)
            assert old_rtype
            container = target.cw_adapt_to('Container').related_container
            parent = req.entity_from_eid(peid)
            parent_container = parent.cw_adapt_to('Container').related_container
            if container.eid != parent_container.eid or old_rtype != self.rtype:
                msg = (req._('%s is already in a container through %s') %
                       (target.e_schema, self.rtype))
                raise ValidationError(target, {self.rtype: msg})
        target.set_relations(container_parent=peid)


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
                continue
            container_rtype_rel[container.container_rtype].append((eid, container.eid))
            container_etype_rel.append((eid, self._container_cwetype_eid(container, cwetype_eid_map)))
        if container_rtype_rel:
            session.add_relations(container_rtype_rel.items())
        if container_etype_rel:
            session.add_relations([('container_etype', container_etype_rel)])

