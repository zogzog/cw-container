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

import logging
from collections import deque, defaultdict

from logilab.common.decorators import cached
from yams.buildobjs import DEFAULT_RELPERMS, RelationType, RelationDefinition

from cubicweb import neg_role, schema as cw_schema
from cubicweb.predicates import EntityPredicate, is_instance

LOGGER = logging.getLogger('cubes.container')
cw_schema.META_RTYPES.update(('container_etype', 'container_parent'))


@cached
def _composite_rschemas(eschema):
    output = []
    for rschema, _types, role in eschema.relation_definitions():
        if rschema.meta or rschema.final:
            continue
        crole = eschema.rdef(rschema, role, takefirst=True).composite
        if crole:
            output.append( (rschema, role, crole) )
    return output

@cached
def _needs_container_parent(eschema):
    return len(list(parent_rschemas(eschema))) > 1

def _define_container_parent_rdefs(schema, etype,
                                   needs_container_parent=_needs_container_parent):
    eschema = schema[etype]
    cparent_rschema = schema['container_parent']
    if needs_container_parent(eschema):
        for peschema in parent_eschemas(eschema):
            petype = peschema.type
            if (etype, petype) not in cparent_rschema.rdefs:
                rdef = RelationDefinition(etype, 'container_parent', petype,
                                          cardinality='?*')
                schema.add_relation_def(rdef)

def parent_eschemas(eschema):
    for rschema, role, crole in _composite_rschemas(eschema):
        if role != crole:
            for eschema in rschema.targets(role=role):
                yield eschema

def parent_rschemas(eschema):
    for rschema, role, crole in _composite_rschemas(eschema):
        if role != crole:
            yield rschema, role

def parent_erschemas(eschema):
    for rschema, role, crole in _composite_rschemas(eschema):
        if role != crole:
            for eschema in rschema.targets(role=role):
                yield rschema, role, eschema

def children_rschemas(eschema):
    for rschema, role, crole in _composite_rschemas(eschema):
        if role == crole:
            yield rschema


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


# Map of container entity type to corresponding container configuration.
CONTAINERS = {}

def register_container(etype, config):
    """Register a container configuration for `etype`"""
    if etype in CONTAINERS:
        raise ValueError('a container configuration for `%s` entity type '
                         'is already registered' % etype)
    CONTAINERS[etype] = config


class ContainerConfiguration(object):
    """Configuration object to turn an entity type into a container.

    Main methods are `define_container`, to be called in `post_build_callback`
    of `schema.py`, `register_container_hooks` and `register_container_protocol` to
    be respectively called in `registration_callback` of `hooks.py` and
    `entities.py`.

    Note about migration: the container relation type (`rtype` attribute)
    should be added and entity types returned by `etypes_to_sync` should be
    synchronized (especially if security rules were added).
    """

    def __init__(self, etype, rtype, skiprtypes=(), skipetypes=(),
                 subcontainers=()):
        self.etype = etype
        self.rtype = rtype
        self.skiprtypes = frozenset(skiprtypes)
        self.skipetypes = frozenset(skipetypes)
        self.subcontainers = frozenset(subcontainers)
        cw_schema.META_RTYPES.add(self.rtype)
        register_container(etype, self)

    def structure(self, schema, strict=False):
        """Return the sets of relation types and entity types that define the
        structure of the container.

        The skeleton (or structure) of the container is determined by following
        composite relations, possibly skipping specified entity types and/or
        relation types.

        When `strict` is True, entity types which entities can live without
        their container (because of cardinality of structural relations) are
        skipped from graph walkthrough and not returned.
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
                # Consider first rdef, assuming they're all consistent (which
                # is normally checked by `_find_spurious_rdefs` call in
                # `define_container`).
                rdef = next(rschema.rdefs.itervalues())
                if rdef.composite != role:
                    continue
                if self.skipetypes.intersection(teschemas):
                    continue
                rtypes.add(rschema.type)
                for teschema in teschemas:
                    etype = teschema.type
                    if etype in etypes.union(self.skipetypes):
                        continue
                    if strict:
                        rdef = eschema.rdef(rschema.type, role=role,
                                            targettype=etype)
                        if rdef.role_cardinality(neg_role(role)) not in '1+':
                            continue
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
        border_rels = set()
        for etype in etypes:
            eschema = schema[etype]
            for rschema, _, role in eschema.relation_definitions():
                if rschema.meta or rschema.final or rschema in skiprtypes:
                    continue
                if (rschema, role) not in border_rels:
                    border_rels.add((rschema, role))
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

    def define_container(self, schema, rtype_permissions=None):
        """Add schema definition for the container configuration

        * insert the container relation type `crtype` in schema (possibly with
          `rtype_permissions`) if not already present.

        * insert all relation definitions `crtype` between the container entity
          type and entities belonging to the container, the latter being defined
          by construction of the container structure (see
          `container_static_structure`).
        """
        rtypes, etypes = self.structure(schema)
        cetype = self.etype
        crtype = self.rtype
        if not crtype in schema:
            # ease pluggability of container in existing applications
            schema.add_relation_type(RelationType(crtype, inlined=True))
        else:
            LOGGER.warning('%r is already defined in the schema - you probably '
                           'want to let it to the container cube', crtype)
        if rtype_permissions is None:
            rtype_permissions = DEFAULT_RELPERMS.copy()
        crschema = schema[crtype]
        cetype_rschema = schema['container_etype']
        for etype in etypes:
            if (etype, cetype) not in crschema.rdefs:
                # checking this will help adding containers to existing
                # applications and reusing the container rtype
                rdef = RelationDefinition(etype, crtype, cetype, cardinality='?*',
                                          __permissions__=rtype_permissions)
                schema.add_relation_def(rdef)
            else:
                LOGGER.warning('%r - %r - %r rdef is already defined in the schema '
                               '- you probably want to let it to the container cube',
                               etype, crtype, cetype)
            if (etype, 'CWEType') not in cetype_rschema.rdefs:
                rdef = RelationDefinition(etype, 'container_etype', 'CWEType',
                                          cardinality='?*')
                schema.add_relation_def(rdef)
            _define_container_parent_rdefs(schema, etype)
        alletypes = etypes.union([self.etype])
        for rtype in rtypes:
            self._check_spurious_rdefs(schema, rtype, alletypes)

    def build_container_hooks(self, schema):
        """Return the container hook with selector set.

        Use this method if you want to subclass generated hooks or control
        registration, else prefer :method:`register_container_hooks` which
        handle potential migration subtleties.
        """
        # Local import because cw.server may not be installed
        from cubicweb.server.hook import Hook, match_rtype
        # Local import because this is a dynamically loaded module.
        from cubes.container import hooks
        parent_rdefs = self._container_parent_rdefs(schema)
        rtypes = self.structure(schema)[0]
        container_rel_hook = type(
            self.etype + 'SetContainerRelation',
            (hooks.SetContainerRelation, ),
            {'_container_parent_rdefs': parent_rdefs,
             '__select__': Hook.__select__ & match_rtype(*rtypes)})
        child_container_rel_hook = type(
            self.etype + 'SetChildContainerRelation',
            (hooks.SetChildContainerRelation, ),
            {'__select__': Hook.__select__ & match_rtype(self.rtype)})
        return container_rel_hook, child_container_rel_hook

    def register_container_hooks(self, vreg):
        """Generate and register hooks to maintain container's internal
        relations.

        During migration, return True if everything went fine, else False in
        case where e.g. the container entity type isn't in the schema yet. If
        not migrating, this would raise an error.

        You will gain finer control by using :method:`build_container_hooks`
        but will have to handle potential migration issues by yourself.
        """
        if not self.etype in vreg.schema and vreg.config.repairing:
            return False
        for hookcls in self.build_container_hooks(vreg.schema):
            vreg.register(hookcls)
        return True

    def build_container_protocol(self, schema):
        """Return a subclass of the ContainerProtocol with selector set.

        Use this method if you want to subclass generated hooks or control
        registration, else prefer :method:`register_container_protocol` which
        handle potential migration subtilities.
        """
        # Local import because this is a dynamically loaded module.
        from cubes.container.entities import ContainerProtocol
        etypes = self.structure(schema)[1]
        # Do not include heads of subcontainers (which are part of the current
        # container) for selection of the current container protocol as these
        # subcontainers will have their own protocol.
        etypes = etypes - self.subcontainers
        selector= is_instance(self.etype, *etypes) & is_in_container(self)
        return type(self.etype + 'ContainerProtocol', (ContainerProtocol, ),
                    {'__select__': selector,
                     'container_rtype': self.rtype})

    def register_container_protocol(self, vreg):
        """Generate and register hooks to maintain container's internal
        relations.

        During migration, return True if everything went fine, else False in
        case where e.g. the container entity type isn't in the schema yet. If
        not migrating, this would raise an error.

        You will gain finer control by using :method:`build_container_protocol`
        but will have to handle potential migration issues by yourself.
        """
        if not self.etype in vreg.schema and vreg.config.repairing:
            return False
        vreg.register(self.build_container_protocol(vreg.schema))
        return True

    # migration helpers ########################################################

    def etypes_to_sync(self, schema):
        """Return the entity types to be synchronized in migration."""
        return self.structure(schema)[1].union([self.etype])

    # internals ################################################################

    def _container_parent_rdefs(self, schema):
        """etypes having several upward paths to the container have a dedicated
        container_parent rtype to speed up the parent computation
        """
        rtypes, etypes = self.structure(schema)
        select_rdefs = defaultdict(set)
        for etype in etypes:
            eschema = schema[etype]
            if not _needs_container_parent(eschema):
                continue
            for rschema, role, teschema in parent_erschemas(eschema):
                if rschema.type in rtypes:
                    if role == 'subject':
                        frometype, toetype = etype, teschema.type
                    else:
                        frometype, toetype = teschema.type, etype
                    select_rdefs[rschema.type].add( (frometype, toetype) )
        return dict(select_rdefs)

    @staticmethod
    def _check_spurious_rdefs(schema, rtype, etypes):
        """Check problematic relation definitions corresponding to a given
        relation type.

        `rtype` is the relation type to check, `etypes` is the set of entity
        types defining the container structure.
        """
        inconsistents, noncomposite = set(), set()
        composites = defaultdict(list)
        for rdef in schema[rtype].rdefs.values():
            if rdef.subject not in etypes or rdef.object not in etypes:
                inconsistents.add(rdef)
            if not rdef.composite:
                noncomposite.add(rdef)
            else:
                # Keep `composite` declarations to make sure they're all
                # consistent.
                composites[rdef.composite].append(rdef)
        if inconsistents:
            LOGGER.warning('rtype %s has rdefs (%s) not part of the '
                           'container structure' %
                           (rtype, ', '.join(map(str, inconsistents))))
        if noncomposite:
            LOGGER.warning('rtype %s has rdefs (%s) which are not composite' %
                           (rtype, ', '.join(map(str, noncomposite))))
        if 'subject' in composites and 'object' in composites:
            LOGGER.warning('rtype %s has rdefs with inconsistent composite '
                           'declarations (subject: %s; object: %s)' %
                           (rtype,
                            ', '.join(map(str, composites['subject'])),
                            ', '.join(map(str, composites['object']))))
