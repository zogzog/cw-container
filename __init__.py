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
    """

    def __init__(self, etype, rtype, skiprtypes=(), skipetypes=(),
                 subcontainers=(), compulsory_hooks_categories=()):
        self.etype = etype
        self.rtype = rtype
        self.skiprtypes = frozenset(skiprtypes)
        self.skipetypes = frozenset(skipetypes)
        self.subcontainers = frozenset(subcontainers)
        self.compulsory_hooks_categories = compulsory_hooks_categories

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
        # Do not include heads of subcontainers (which are part of the current
        # container) for selection of the current container protocol as these
        # subcontainers will have their own protocol.
        skipetypes = self.skipetypes.union(self.subcontainers)
        _, etypes = utils.container_static_structure(
            schema, self.etype, self.rtype, skiprtypes=self.skiprtypes,
            skipetypes=skipetypes, subcontainers=self.subcontainers)
        return type(self.etype + 'ContainerProtocol', (ContainerProtocol, ),
                    {'__select__': is_instance(self.etype, *etypes) & is_in_container(self),
                     'container_rtype': self.rtype})
