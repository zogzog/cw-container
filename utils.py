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

from logilab.common.deprecation import deprecated

from rql.nodes import Comparison, VariableRef, make_relation

from cubes.container import (ContainerConfiguration, _needs_container_parent,
                             parent_eschemas, parent_rschemas,
                             parent_erschemas, children_rschemas, CONTAINERS)


def composite_role(eschema, rschema):
    """ testing compositeness is a bit awkward with the standard
    yams API (due to potentially multirole relation definitions) """
    try:
        return eschema.rdef(rschema, 'subject', takefirst=True).composite
    except KeyError:
        return eschema.rdef(rschema, 'object', takefirst=True).composite

@deprecated('[container 2.4] not a public api anymore')
def needs_container_parent(eschema):
    return _needs_container_parent(eschema)

def _get_config(cetype, *args, **kwargs):
    """Retrieve or build a container configuration avoiding registration
    duplicates. Mostly useful for *deprecated* functions which do not use a
    ContainerConfiguration directly but would build one.
    """
    if cetype in CONTAINERS:
        return CONTAINERS[cetype]
    else:
        return ContainerConfiguration(etype, *args, **kwargs)

@deprecated('[container 2.4] use ContainerConfiguration')
def define_container(schema, cetype, crtype, rtype_permissions=None,
                     skiprtypes=(), skipetypes=(), subcontainers=()):
    """Handle container definition in schema

    * insert the container relation type `crtype` in schema (possibly with
      `rtype_permissions`) if not already present.

    * insert all relation definitions `crtype` between the container
      entity type and entities belonging to the container, the latter
      being defined by construction of the container structure (see
      `container_static_structure`).
    """
    cfg = _get_config(cetype, crtype,
                      skiprtypes=skiprtypes, skipetypes=skipetypes,
                      subcontainers=subcontainers)
    cfg.define_container(schema, rtype_permissions)

@deprecated('[container 2.4] use ContainerConfiguration')
def define_container_parent_rdefs(schema, etype,
                                  needs_container_parent=_needs_container_parent):
    from cubes.container import _define_container_parent_rdefs
    _define_container_parent_rdefs(schema, etype, needs_container_parent)

@deprecated('[container 2.4] use ContainerConfiguration.structure')
def container_static_structure(schema, cetype, crtype, skiprtypes=(), skipetypes=(),
                               subcontainers=()):
    """Return the sets of entity types and relation types that define the
    structure of the container.

    The skeleton (or structure) of the container is determined by following
    composite relations, possibly skipping specified entity types and/or
    relation types.
    """
    cfg = _get_config(cetype, crtype,
                      skiprtypes=skiprtypes, skipetypes=skipetypes,
                      subcontainers=subcontainers)
    return cfg.structure(schema)

@deprecated('[container 2.1] the container_parent hook is merged into another; '
            'please read the upgrade instructions')
def set_container_parent_rtypes_hook(schema, cetype, crtype, skiprtypes=(), skipetypes=(),
                                     subcontainers=()):
    """ etypes having several upward paths to the container have a dedicated container_parent
    rtype to speed up the parent computation
    this function computes the rtype set needed for the SetContainerParent hook selector
    """
    cfg = _get_config(cetype, crtype,
                      skiprtypes=skiprtypes, skipetypes=skipetypes,
                      subcontainers=subcontainers)
    rtypes, etypes = cfg.structure(schema)
    select_rtypes = set()
    for etype in etypes:
        eschema = schema[etype]
        prschemas = list(parent_rschemas(eschema))
        if len(prschemas) > 1:
            for rschema, role in prschemas:
                if rschema.type in rtypes:
                    select_rtypes.add(rschema.type)
    return select_rtypes

@deprecated('[container 2.4] use ContainerConfiguration')
def container_parent_rdefs(schema, cetype, crtype, skiprtypes=(), skipetypes=(),
                           subcontainers=()):
    """ etypes having several upward paths to the container have a dedicated container_parent
    rtype to speed up the parent computation

    usage:

      rdefs_select = container_parent_hook_selector(...)
      SetContainerRelation._container_parent_rdefs = rdefs_select
    """
    cfg = _get_config(cetype, crtype,
                      skiprtypes=skiprtypes, skipetypes=skipetypes,
                      subcontainers=subcontainers)
    return cfg._container_parent_rdefs(schema)


@deprecated('[container 2.4] use ContainerConfiguration')
def set_container_relation_rtypes_hook(schema, cetype, crtype, skiprtypes=(), skipetypes=(),
                                       subcontainers=()):
    """computes the rtype set needed for etypes having just one upward
    path to the container, to be given to the SetContainerRealtion hook
    """
    cfg = _get_config(cetype, crtype,
                      skiprtypes=skiprtypes, skipetypes=skipetypes,
                      subcontainers=subcontainers)
    return cfg.structure(schema)[0]


@deprecated('[container 2.4] use ContainerConfiguration.structure and/or .inner_rtypes ')
def container_rtypes_etypes(schema, cetype, crtype, skiprtypes=(), skipetypes=(),
                            subcontainers=()):
    """Return all entity types and relation types that are part of the container.

    It extends ``container_static_structure`` with non structural relation types
    between entity types belonging to the defining structure of the container.
    """
    cfg = _get_config(cetype, crtype,
                      skiprtypes=skiprtypes, skipetypes=skipetypes,
                      subcontainers=subcontainers)
    rtypes, etypes = cfg.structure(schema)
    return rtypes.union(cfg.inner_relations(schema)), etypes


def border_rtypes(schema, etypes, inner_rtypes):
    """ compute the set of rtypes that go from/to an etype in a container
    to/from an etype outside
    """
    border_crossing = set()
    for etype in etypes:
        eschema = schema[etype]
        for rschema, _teschemas, _role in eschema.relation_definitions():
            if rschema.meta or rschema.final:
                continue
            if rschema.type in inner_rtypes:
                continue
            border_crossing.add(rschema.type)
    return border_crossing


# clone helpers

def _add_rqlst_restriction(rqlst, rtype, optional=False):
    """pick up the main (first) selected variable and add an rtype constraint

    if `optional` is True, use a left-outer join on the new variable.

       Any X WHERE X is Case => Any X,FOO WHERE X is Case, X foo FOO
    """
    main_var = rqlst.get_variable(rqlst.get_selected_variables().next().name)
    new_var = rqlst.make_variable()
    rqlst.add_selected(new_var)
    rel = make_relation(main_var, rtype, (new_var,), VariableRef)
    rqlst.add_restriction(rel)
    if optional:
        rel.change_optional('right')

def _iter_mainvar_relations(rqlst):
    """pick up the main (first) selected variable and yield
    tuples (rtype, dest_var) for each restriction found in the ST
    with the main variable as subject.

    For instance, considering the following RQL query::

        Any X WHERE X foo Y, X bar 3, X baz Z

    the function would yield::

      ('foo', Y), ('baz', Z)

    """
    main_var = rqlst.get_variable(rqlst.get_selected_variables().next().name)
    for vref in main_var.references():
        rel = vref.relation()
        # XXX we should ignore relations found in a subquery or EXISTS
        if rel is not None and rel.children[0] == vref:
            if (isinstance(rel.children[1], Comparison)
                and isinstance(rel.children[1].children[0], VariableRef)):
                yield rel.r_type, rel.children[1].children[0]


def _insertmany(session, table, attributes, prefix=''):
    """ Low-level INSERT many entities of the same etype
    at once
    """
    # the low-level python-dbapi cursor
    cursor = session.cnxset['system']
    columns = sorted(attributes[0])
    cursor.executemany('INSERT INTO %s (%s) VALUES (%s)' % (
        prefix + table,                                    # table name
        ','.join(prefix + name for name in columns),       # column names
        ','.join('%%(%s)s' %  name for name in columns)),  # dbapi placeholders
                       attributes)

# migration helper

def synchronize_container_parent_rdefs(schema,
                                       add_relation_definition,
                                       drop_relation_definition,
                                       cetype, crtype, skiprtypes, skipetypes):
    """ To be used in migration involving added/removed etypes in a container
    It will automatically add/remove rdefs for the `container_parent` rtype.

    example usage:

      from mycube.entities.box import Box # Box is a container etype
      synchronize_container_parent_rdefs(schema,
                                         add_relation_definition,
                                         drop_relation_definition,
                                         Box.__regid__,
                                         Box.container_rtype,
                                         Box.container_skiprtypes,
                                         Box.container_skipetypes)
    """
    _rtypes, etypes = container_static_structure(schema, cetype, crtype, skiprtypes, skipetypes)
    cparent = schema['container_parent']
    for etype in etypes:
        eschema = schema[etype]
        if _needs_container_parent(eschema):
            for peschema in parent_eschemas(eschema):
                if (eschema, peschema) not in cparent.rdefs:
                    add_relation_definition(etype, 'container_parent', peschema.type)

    def unneeded_container_parent_rdefs():
        rdefs = []
        for subj, obj in cparent.rdefs:
            if not _needs_container_parent(subj):
                rdefs.append((subj, obj))
        return rdefs

    for subj, obj in unneeded_container_parent_rdefs():
        drop_relation_definition(subj.type, 'container_parent', obj.type)
