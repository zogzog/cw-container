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

from collections import defaultdict
from warnings import warn
import logging

from logilab.common.deprecation import deprecated

from rql.nodes import Comparison, VariableRef, make_relation

from cubicweb import neg_role
from cubicweb.appobject import Predicate

from cubes.container import ContainerConfiguration, _needs_container_parent, CONTAINERS

logger = logging.getLogger()

class yet_unset(Predicate):
    # can't use class_deprecated here because
    # "the metaclass of a derived class must be a
    # (non-strict) subclass of the metaclasses of all its bases"
    # and Predicate already has its own (incompatible) metaclass
    __deprecation_warning__ = '[container 2.4] you should drop any usage of this'

    def __call__(self, cls, *args, **kwargs):
        warn(self.__deprecation_warning__,
             DeprecationWarning)
        warn('%s has no selector set' % cls)
        return 0

def fsschema(schema):
    """predicate telling whether the schema comes from the filesystem of
    the repository

    """
    return getattr(schema, 'fs', False)

def composite(rdef):
    """ Return the `composite` eschema of a relation definition """
    if rdef.composite is None:
        return None
    return rdef.subject if rdef.composite == 'subject' else rdef.object

def component(rdef):
    """ Return the `component` part of a composite relation  """
    if rdef.composite is None:
        return None
    return rdef.object if rdef.composite == 'subject' else rdef.subject

def iterrdefs(eschema, meta=True, final=True, skiprtypes=(), skipetypes=()):
    """ yield all the relation definitions of an entity type """
    for role in ('subject', 'object'):
        rschemas = eschema.subjrels if role == 'subject' else eschema.objrels
        for rschema in rschemas:
            if not meta and rschema.meta:
                continue
            if not final and rschema.final:
                continue
            if rschema in skiprtypes:
                continue
            for rdef in rschema.rdefs.itervalues():
                if getattr(rdef, neg_role(role)) in skipetypes:
                    continue
                if getattr(rdef, role) == eschema:
                    yield rdef

@deprecated('[container 2.4] there are better ways')
def composite_role(eschema, rschema):
    """ testing compositeness is a bit awkward with the standard
    yams API (due to potentially multirole relation definitions) """
    try:
        return eschema.rdef(rschema, 'subject', takefirst=True).composite
    except KeyError:
        return eschema.rdef(rschema, 'object', takefirst=True).composite

@deprecated('[container 2.4] there are better ways')
def _composite_rschemas(eschema):
    output = []
    for rschema, _types, role in eschema.relation_definitions():
        if rschema.meta or rschema.final:
            continue
        crole = eschema.rdef(rschema, role, takefirst=True).composite
        if crole:
            output.append( (rschema, role, crole) )
    return output

def parent_eschemas(eschema):
    for rschema, role, crole in _composite_rschemas(eschema):
        if role != crole:
            for eschema in rschema.targets(role=role):
                yield eschema

@deprecated('[container 2.4] use parent_rdefs instead')
def parent_rschemas(eschema):
    for rschema, role, crole in _composite_rschemas(eschema):
        if role != crole:
            yield rschema, role

@deprecated('[container 2.4] there are better ways')
def parent_erschemas(eschema):
    for rschema, role, crole in _composite_rschemas(eschema):
        if role != crole:
            for eschema in rschema.targets(role=role):
                yield rschema, role, eschema

def parent_rdefs(eschema):
    """Yield all the rdefs leading to a composite (or `parent`)
    eschema. We must take care of etypes that are composed of
    themselves.
    """
    for rdef in iterrdefs(eschema, meta=False, final=False):
        if rdef.composite:
            composite_eschema = composite(rdef)
            if composite_eschema == eschema:
                component_eschema = component(rdef)
                if component_eschema != eschema:
                    continue
            yield rdef

def children_rdefs(eschema):
    """Yield all the rdefs leading to a component (or `child`)
    eschema. We must take care of etypes that are composed of
    themselves.
    """
    for rdef in iterrdefs(eschema, meta=False, final=False):
        if rdef.composite:
            component_eschema = component(rdef)
            if component_eschema == eschema:
                composite_eschema = composite(rdef)
                if composite_eschema != eschema:
                    continue
            yield rdef

# still used, but should die
def children_rschemas(eschema):
    for rschema, role, crole in _composite_rschemas(eschema):
        if role == crole:
            yield rschema

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
        return ContainerConfiguration(cetype, *args, **kwargs)

@deprecated('[container 2.4] you should switch to the config.Container object')
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

@deprecated('[container 2.4] you should switch to the config.Container object')
def define_container_parent_rdefs(schema, etype,
                                  needs_container_parent=_needs_container_parent):
    from cubes.container import _define_container_parent_rdefs
    _define_container_parent_rdefs(schema, etype, needs_container_parent)

@deprecated('[container 2.4] you should switch to the config.Container object')
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

@deprecated('[container 2.4] you should switch to the config.Container object')
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


@deprecated('[container 2.4] you should switch to the config.Container object')
def set_container_relation_rtypes_hook(schema, cetype, crtype, skiprtypes=(), skipetypes=(),
                                       subcontainers=()):
    """computes the rtype set needed for etypes having just one upward
    path to the container, to be given to the SetContainerRealtion hook
    """
    cfg = _get_config(cetype, crtype,
                      skiprtypes=skiprtypes, skipetypes=skipetypes,
                      subcontainers=subcontainers)
    return cfg.structure(schema)[0]


@deprecated('[container 2.4] you should switch to the config.Container object')
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


@deprecated('[container 2.4] you should switch to the config.Container object')
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


@deprecated('[container 2.4] you should switch to the config.Container object')
def needed_etypes(schema, etype, cetype, crtype, computed_rtypes=()):
    """ finds all container etypes this one depends on to be built
    start from all subject + object relations """
    etypes = defaultdict(list)
    skipetypes = set((cetype,))
    # these should include rtypes
    # that create cycles but actually are false dependencies
    skiprtypes = set(computed_rtypes).union((crtype, 'container_etype', 'container_parent'))
    skiprtypes.add(crtype)
    eschema = schema[etype]
    adjacent_rtypes = [(rschema.type, role)
                       for role in ('subject', 'object')
                       for rschema in getattr(eschema, '%s_relations' % role)()
                       if not (rschema.meta or rschema.final or rschema.type in skiprtypes)]
    children_rtypes = [r.type for r in children_rschemas(eschema)]
    parent_etypes = set(parent_eschemas(eschema))
    for rtype, role in adjacent_rtypes:
        if rtype in children_rtypes:
            continue
        rdef = eschema.rdef(rtype, role)
        target = getattr(rdef, neg_role(role))
        if target.type in skipetypes:
            continue
        if target.type not in parent_etypes:
            if rdef.cardinality[0 if role == 'subject' else 1] in '?*':
                continue
        etypes[target.type].append((rdef, role))
    return etypes

def linearize(etype_map, all_etypes):
    # Kahn 1962
    sorted_etypes = []
    independent = set()
    for etype, deps in etype_map.items():
        if not deps:
            independent.add(etype)
            del etype_map[etype]
        for depetype in deps:
            if depetype not in all_etypes:
                # out of container dependencies must be added
                # to complete the graph
                etype_map[depetype] = dict()
    while independent:
        indep_etype = min(independent) # get next in ascii order
        independent.remove(indep_etype)
        sorted_etypes.append(indep_etype)
        for etype, incoming in etype_map.items():
            if indep_etype in incoming:
                incoming.pop(indep_etype)
            if not incoming:
                independent.add(etype)
                etype_map.pop(etype)
    return [etype for etype in sorted_etypes
            if etype in all_etypes]

@deprecated('[container 2.4] you should switch to the config.Container object')
def ordered_container_etypes(schema, cetype, crtype, skiprtypes=(), skipetypes=(),
                             subcontainers=()):
    """ return list of etypes of a container by dependency order
    this is provided for simplicity and backward compatibility
    reasons
    etypes that are parts of a cycle are undiscriminately
    added at the end
    """
    orders, etype_map = container_etype_orders(schema, cetype, crtype,
                                               skiprtypes, skipetypes, subcontainers)
    total_order = []
    for order in orders:
        total_order += order
    return total_order + etype_map.keys()

@deprecated('[container 2.4] you should switch to the config.Container object')
def container_etype_orders(schema, cetype, crtype, skiprtypes=(), skipetypes=(),
                           subcontainers=()):
    """ computes linearizations and cycles of etypes within a container """
    _rtypes, etypes = container_static_structure(schema, cetype, crtype,
                                                 skiprtypes=skiprtypes,
                                                 skipetypes=skipetypes,
                                                 subcontainers=subcontainers)
    orders = []
    etype_map = dict((etype, needed_etypes(schema, etype, cetype, crtype,
                                           skiprtypes))
                     for etype in etypes)
    maplen = len(etype_map)
    while etype_map:
        neworder = linearize(etype_map, etypes)
        if neworder:
            orders.append(neworder)
        if maplen == len(etype_map):
            break
        maplen = len(etype_map)
    return orders, etype_map


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
