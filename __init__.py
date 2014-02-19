# copyright 2013-2014 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of CubicWeb.
#
# CubicWeb is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 2.1 of the License, or (at your option)
# any later version.
#
# CubicWeb is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with CubicWeb.  If not, see <http://www.gnu.org/licenses/>.
"""cubicweb-container application package

provides "generic container" services
"""
from collections import deque

from cubicweb import neg_role

from cubicweb import schema
from cubicweb.predicates import EntityPredicate, is_instance
from cubicweb.server.hook import Hook, match_rtype

from cubes.container import utils


schema.META_RTYPES.update(('container_etype', 'container_parent'))

class is_in_container(EntityPredicate):
    """Selector adding bonus points if the entity adapted to `ContainerProtocol`
    is in the container whose configuration has been given as argument.

    Add 2 to the score if the entity is in the bound container configuration,
    else 1 as we don't want to discard the selected object, only give priority
    to one or another.
    """
    def __init__(self, container_config):
        super(is_in_container, self).__init__()
        self.container_config = container_config

    def score_entity(self, entity):
        if entity.cw_etype == self.container_config.etype:
            return 2
        if getattr(entity, self.container_config.rtype):
            return 2
        return 1


class ContainerConfiguration(object):
    """Configuration object to turn an entity type into a container.

    Main methods are `define_container`, to be called in `post_build_callback`
    of `schema.py`, `build_container_hook` and `build_container_protocol` to
    be respectively called in `registration_callback` of `hooks.py` and
    `entities.py`.

    Note about migration: the container relation type (`rtype` attribute)
    should be added and entity types returned by `etypes_to_sync` should be
    synchronized (especially if security rules were added).
    """

    def __init__(self, etype, rtype, skiprtypes=(), skipetypes=(),
                 subcontainers=(), compulsory_hooks_categories=()):
        self.etype = etype
        self.rtype = rtype
        self.skiprtypes = frozenset(skiprtypes)
        self.skipetypes = frozenset(skipetypes)
        self.subcontainers = frozenset(subcontainers)
        self.compulsory_hooks_categories = compulsory_hooks_categories

    def structure(self, schema):
        """Return the sets of relation types and entity types that define the
        structure of the container.

        The skeleton (or structure) of the container is determined by following
        composite relations, possibly skipping specified entity types and/or
        relation types.
        """
        etypes = set()
        rtypes = set()
        skiprtypes = self.skiprtypes.union((self.rtype, 'container_etype',
                                            'container_parent'))
        candidates = deque([schema[self.etype]])
        while candidates:
            eschema = candidates.pop()
            if eschema.type in self.subcontainers:
                etypes.add(eschema.type)
                # however we stop right here as the subcontainer is responsible
                # for his own stuff
                continue
            for rschema, teschemas, role in eschema.relation_definitions():
                if rschema.meta or rschema in skiprtypes:
                    continue
                if not rschema.rdefs.itervalues().next().composite == role:
                    continue
                if self.skipetypes.intersection(teschemas):
                    continue
                rtypes.add(rschema.type)
                for teschema in teschemas:
                    etype = teschema.type
                    if etype not in etypes and etype not in self.skipetypes:
                        candidates.append(teschema)
                        etypes.add(etype)
        return set(rtypes), set(etypes)

    def inner_relations(self, schema):
        """Yield rschema for all non-structural relations between entity types
        which are part of the container.

        `rschema` is the relation schema.
        """
        rtypes, etypes = self.structure(schema)
        rtypes.add(self.rtype) # ensure container relation isn't yielded
        for rschema in schema.relations():
            if rschema.meta or rschema.final or rschema.type in rtypes:
                continue
            for subjtype, objtype in rschema.rdefs:
                if subjtype in etypes and objtype in etypes:
                    yield rschema
                    break

    def border_relations(self, schema):
        """Yield (rschema, role) for relations where some extremity is outside
        the container graph and the other inside.

        `rschema` is the relation schema, `role` is the role of the entity
        inside the container in the relation.
        """
        rtypes, etypes = self.structure(schema)
        skiprtypes = rtypes.union(self.inner_relations(schema))
        skiprtypes = skiprtypes.union(self.skiprtypes)
        for etype in etypes:
            eschema = schema[etype]
            for rschema, _, role in eschema.relation_definitions():
                if rschema.meta or rschema.final or rschema in skiprtypes:
                    continue
                yield rschema, role

    def structural_relations_to_container(self, schema):
        """Yield (rschema, role) for relations in the container graph directly
        leading to the root.

        `rschema` is the relation schema, `role` is the role of the root
        (a.k.a container) in the relation.
        """
        for rtype in self.structure(schema)[0]:
            rschema = schema.rschema(rtype)
            for role in ('subject', 'object'):
                if rschema.targets(role=role)[0].type == self.etype:
                    yield rschema, neg_role(role)
                    break

    def structural_relations_to_parent(self, schema):
        """Yield (rschema, role) for relations in the container graph but not
        directly leading to the root.

        `rschema` is the relation schema, `role` is the role of the parent in
        the relation.
        """
        for rtype in self.structure(schema)[0]:
            rschema = schema.rschema(rtype)
            for role in ('subject', 'object'):
                if rschema.targets(role=role)[0].type == self.etype:
                    break
            else:
                role = rschema.rdefs.itervalues().next().composite
                yield rschema, role

    # container setup methods ##################################################

    def define_container(self, schema):
        """Add schema definition for the container configuration"""
        utils.define_container(schema, self.etype, self.rtype,
                               skiprtypes=self.skiprtypes,
                               skipetypes=self.skipetypes,
                               subcontainers=self.subcontainers)

    def build_container_hook(self, schema):
        """Return the container hook with selector set"""
        # Local import because this is a dynamically loaded module.
        from cubes.container.hooks import SetContainerRelation
        parent_rdefs = utils.container_parent_rdefs(
            schema, self.etype, self.rtype, skiprtypes=self.skiprtypes,
            skipetypes=self.skipetypes, subcontainers=self.subcontainers)
        rtypes = utils.set_container_relation_rtypes_hook(
            schema, self.etype, self.rtype, skiprtypes=self.skiprtypes,
            skipetypes=self.skipetypes, subcontainers=self.subcontainers)
        return type(self.etype + 'SetContainerRelation',
                    (SetContainerRelation, ),
                    {'_container_parent_rdefs': parent_rdefs,
                     '__select__': Hook.__select__ & match_rtype(*rtypes)})

    def build_container_protocol(self, schema):
        """Return a subclass of the ContainerProtocol with selector set"""
        # Local import because this is a dynamically loaded module.
        from cubes.container.entities import ContainerProtocol
        etypes = self.structure(schema)[1]
        # Do not include heads of subcontainers (which are part of the current
        # container) for selection of the current container protocol as these
        # subcontainers will have their own protocol.
        etypes = etypes - self.subcontainers
        return type(self.etype + 'ContainerProtocol', (ContainerProtocol, ),
                    {'__select__': is_instance(self.etype, *etypes) & is_in_container(self),
                     'container_rtype': self.rtype})

    # migration helpers ########################################################

    def etypes_to_sync(self, schema):
        """Return the entity types to be synchronized in migration."""
        return self.structure(schema)[1].union([self.etype])
