from collections import deque, defaultdict
from warnings import warn
import logging

from logilab.common.decorators import cached

from yams.buildobjs import RelationType, RelationDefinition

from rql import parse
from rql.nodes import Comparison, VariableRef, make_relation

from cubicweb import neg_role, schema as cw_schema
from cubicweb.appobject import Predicate

logger = logging.getLogger()

class yet_unset(Predicate):
    def __call__(self, cls, *args, **kwargs):
        warn('%s has no selector set' % cls)
        return 0


def composite_role(eschema, rschema):
    """ testing compositeness is a bit awkward with the standard
    yams API (due to potentially multirole relation definitions) """
    try:
        return eschema.rdef(rschema, 'subject').composite
    except KeyError:
        return eschema.rdef(rschema, 'object').composite

@cached
def _composite_rschemas(eschema):
    output = []
    for rschema, _types, role in eschema.relation_definitions():
        if rschema.meta or rschema.final:
            continue
        crole = eschema.rdef(rschema, role).composite
        if crole:
            output.append( (rschema, role, crole) )
    return output

def parent_eschemas(eschema):
    for rschema, role, crole in _composite_rschemas(eschema):
        if role != crole:
            for eschema in rschema.targets(role=role):
                yield eschema

def parent_rschemas(eschema):
    for rschema, role, crole in _composite_rschemas(eschema):
        if role != crole:
            yield rschema, role

def children_rschemas(eschema):
    for rschema, role, crole in _composite_rschemas(eschema):
        if role == crole:
            yield rschema

@cached
def needs_container_parent(eschema):
    return len(list(parent_rschemas(eschema))) > 1

def define_container(schema, cetype, crtype, rtype_permissions=None,
                     skiprtypes=(), skipetypes=()):
    _rtypes, etypes = container_static_structure(schema, cetype, crtype,
                                                 skiprtypes=skiprtypes,
                                                 skipetypes=skipetypes)
    if not crtype in schema:
        # ease pluggability of container in existing applications
        schema.add_relation_type(RelationType(crtype, inlined=True))
        cw_schema.META_RTYPES.add(crtype)
    else:
        logger.warning('%r is already defined in the schema - you probably want '
                       'to let it to the container cube' % crtype)
    if rtype_permissions is None:
        rtype_permissions = {'read': ('managers', 'users'),
                             'add': ('managers', 'users'),
                             'delete': ('managers', 'users')}
        schema.warning('setting standard lenient permissions on %s relation', crtype)
    crschema = schema[crtype]
    cetype_rschema = schema['container_etype']
    cparent_rschema = schema['container_parent']
    for etype in etypes:
        if (etype, cetype) not in crschema.rdefs:
            # checking this will help adding containers to existing applications
            # and reusing the container rtype
            schema.add_relation_def(RelationDefinition(etype, crtype, cetype, cardinality='?*',
                                                       __permissions__=rtype_permissions))
        else:
            logger.warning('%r - %r - %r rdef is already defined in the schema - you probably '
                           'want to let it to the container cube' % (etype, crtype, cetype))
        if (etype, 'CWEType') not in cetype_rschema.rdefs:
            schema.add_relation_def(RelationDefinition(etype, 'container_etype', 'CWEType',
                                                       cardinality='?*'))
        eschema = schema[etype]
        if needs_container_parent(eschema):
            for peschema in parent_eschemas(eschema):
                petype = peschema.type
                if (etype, petype) not in cparent_rschema.rdefs:
                    schema.add_relation_def(RelationDefinition(etype, 'container_parent', petype,
                                                               cardinality='?*'))


def container_static_structure(schema, cetype, crtype, skiprtypes=(), skipetypes=()):
    """ return etypes and composite rtypes (the rtypes
    that _define_ the structure of the Container graph)
    """
    skiprtypes = set(skiprtypes).union((crtype, 'container_etype', 'container_parent'))
    skipetypes = set(skipetypes)
    etypes = set()
    rtypes = set()
    candidates = deque([schema[cetype]])
    while candidates:
        eschema = candidates.pop()
        for rschema, teschemas, role in eschema.relation_definitions():
            if rschema.meta or rschema in skiprtypes:
                continue
            if not composite_role(eschema, rschema) == role:
                continue
            rtypes.add(rschema.type)
            for teschema in teschemas:
                etype = teschema.type
                if etype not in etypes and etype not in skipetypes:
                    candidates.append(teschema)
                    etypes.add(etype)
    return frozenset(rtypes), frozenset(etypes)


def set_container_parent_rtypes_hook(schema, cetype, crtype, skiprtypes=(), skipetypes=()):
    """ etypes having several upward paths to the container have a dedicated container_parent
    rtype to speed up the parent computation
    this function computes the rtype set needed for the SetContainerParent hook selector
    """
    rtypes, etypes = container_static_structure(schema, cetype, crtype,
                                                skiprtypes=skiprtypes, skipetypes=skipetypes)
    select_rtypes = set()
    for etype in etypes:
        eschema = schema[etype]
        prschemas = list(parent_rschemas(eschema))
        if len(prschemas) > 1:
            for rschema, role in prschemas:
                if rschema.type in rtypes:
                    select_rtypes.add(rschema.type)
    return select_rtypes


def set_container_relation_rtypes_hook(schema, cetype, crtype, skiprtypes=(), skipetypes=()):
    """computes the rtype set needed for etypes having just one upward
    path to the container, to be given to the SetContainerRealtion hook
    """
    rtypes, etypes = container_static_structure(schema, cetype, crtype, skiprtypes, skipetypes)
    # the container_parent rtype will be set for these etypes having several upard paths
    # to the container through the SetContainerParent hook
    cp_rtypes = set_container_parent_rtypes_hook(schema, cetype, crtype, skiprtypes, skipetypes)
    return rtypes - cp_rtypes


def container_rtypes_etypes(schema, cetype, crtype, skiprtypes=(), skipetypes=()):
    """ returns set of rtypes, set of etypes of what is in a Container """
    skiprtypes = set(skiprtypes).union((crtype,'container_etype', 'container_parent'))
    rtypes, etypes = container_static_structure(schema, cetype, crtype,
                                                skiprtypes, skipetypes)
    rtypes = set(rtypes)
    for etype in etypes:
        eschema = schema[etype]
        for rschema, _teschemas, role in eschema.relation_definitions():
            if rschema.meta:
                continue
            rtype = rschema.type
            if rtype in rtypes or rtype in skiprtypes:
                continue
            reletypes = set(eschema.type
                            for eschema in rschema.targets(role=role)
                            if eschema.type in etypes)
            if not reletypes:
                continue
            rtypes.add(rtype)
    return frozenset(rtypes), frozenset(etypes)


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

def ordered_container_etypes(schema, cetype, crtype, skiprtypes=()):
    """ return list of etypes of a container by dependency order
    this is provided for simplicity and backward compatibility
    reasons
    etypes that are parts of a cycle are undiscriminately
    added at the end
    """
    orders, etype_map = container_etype_orders(schema, cetype, crtype, skiprtypes)
    total_order = []
    for order in orders:
        total_order += order
    return total_order + etype_map.keys()

def container_etype_orders(schema, cetype, crtype, skiprtypes=()):
    """ computes linearizations and cycles of etypes within a container """
    _rtypes, etypes = container_static_structure(schema, cetype, crtype,
                                                 skiprtypes=skiprtypes)
    orders = []
    etype_map = dict((etype, needed_etypes(schema, etype, cetype, crtype,
                                           skiprtypes))
                     for etype in etypes)
    maplen = len(etype_map)
    def _append_order():
        neworder = linearize(etype_map, etypes)
        if neworder:
            orders.append(neworder)
    while etype_map:
        _append_order()
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
