from collections import deque, defaultdict
from warnings import warn

from logilab.common.decorators import cached

from yams.buildobjs import RelationType, RelationDefinition

from cubicweb import neg_role
from cubicweb.appobject import Selector

class yet_unset(Selector):
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

def children_rschemas(eschema):
    for rschema, role, crole in _composite_rschemas(eschema):
        if role == crole:
            yield rschema

def define_container(schema, cetype, crtype, rtype_permissions=None,
                     skiprtypes=(), skipetypes=()):
    _rtypes, etypes = container_static_structure(schema, cetype, crtype,
                                                 skiprtypes=skiprtypes,
                                                 skipetypes=skipetypes)
    schema.add_relation_type(RelationType(crtype, inlined=True))
    if rtype_permissions is None:
        rtype_permissions = {'read': ('managers', 'users'),
                             'add': ('managers', 'users'),
                             'delete': ('managers', 'users')}
        schema.warning('setting standard lenient permissions on %s relation', crtype)
    for etype in etypes:
        schema.add_relation_def(RelationDefinition(etype, crtype, cetype, cardinality='?*',
                                                   __permissions__=rtype_permissions))
        try: # prevent multiple definitions (some etypes can be hosted by several containers)
            schema['container_etype'].rdef(etype, 'CWEType')
        except KeyError:
            schema.add_relation_def(RelationDefinition(etype, 'container_etype', 'CWEType',
                                                       cardinality='?*'))
        for peschema in parent_eschemas(schema[etype]):
            petype = peschema.type
            try: # etype in multiple container
                schema['container_parent'].rdef(etype, petype)
            except KeyError:
                schema.add_relation_def(RelationDefinition(etype, 'container_parent', petype,
                                                           cardinality='?*'))
    rtypes, etypes = container_static_structure(schema, cetype, crtype)
    from cubes.container import hooks
    hooks.ALL_CONTAINER_RTYPES.update(rtypes)
    hooks.ALL_CONTAINER_ETYPES.update(etypes)


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
