# copyright 2011-2015 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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

import logging

from logilab.common.deprecation import deprecated

from rql.nodes import Comparison, VariableRef, make_relation

from cubicweb import neg_role


logger = logging.getLogger()


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
    seen = set()
    for rdef in parent_rdefs(eschema):
        eschema = composite(rdef)
        if eschema.type in seen:
            continue
        seen.add(eschema.type)
        yield eschema

def dual(role):
    return 'subject' if role == 'object' else 'object'

def parent_rschemas(eschema):
    seen = set()
    for rdef in parent_rdefs(eschema):
        rschema = rdef.rtype
        if (rschema, rdef.composite) in seen:
            continue
        seen.add((rschema, rdef.composite))
        yield rschema, dual(rdef.composite)

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
    # NOTE: this must be fixed using rdefs
    return len(set(rdef.rtype.type for rdef in parent_rdefs(eschema))) > 1


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

