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

from collections import deque, defaultdict
from warnings import warn
import logging

from logilab.common.decorators import cached, monkeypatch
from logilab.common.deprecation import deprecated

from yams.buildobjs import RelationType, RelationDefinition

from rql import parse
from rql.nodes import Comparison, VariableRef, make_relation

from cubicweb import neg_role, schema as cw_schema
from cubicweb.appobject import Predicate

from cubicweb.server.sources.native import NativeSQLSource

logger = logging.getLogger()

class yet_unset(Predicate):
    def __call__(self, cls, *args, **kwargs):
        warn('%s has no selector set' % cls)
        return 0


def composite_role(eschema, rschema):
    """ testing compositeness is a bit awkward with the standard
    yams API (due to potentially multirole relation definitions) """
    try:
        return eschema.rdef(rschema, 'subject', takefirst=True).composite
    except KeyError:
        return eschema.rdef(rschema, 'object', takefirst=True).composite

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

@cached
def needs_container_parent(eschema):
    return len(list(parent_rschemas(eschema))) > 1

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
    _rtypes, etypes = container_static_structure(schema, cetype, crtype,
                                                 skiprtypes=skiprtypes,
                                                 skipetypes=skipetypes,
                                                 subcontainers=subcontainers)
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
        define_container_parent_rdefs(schema, etype)

def define_container_parent_rdefs(schema, etype,
                                  needs_container_parent=needs_container_parent):
    eschema = schema[etype]
    cparent_rschema = schema['container_parent']
    if needs_container_parent(eschema):
        for peschema in parent_eschemas(eschema):
            petype = peschema.type
            if (etype, petype) not in cparent_rschema.rdefs:
                schema.add_relation_def(RelationDefinition(etype, 'container_parent', petype,
                                                           cardinality='?*'))


def container_static_structure(schema, cetype, crtype, skiprtypes=(), skipetypes=(),
                               subcontainers=()):
    """Return the sets of entity types and relation types that define the
    structure of the container.

    The skeleton (or structure) of the container is determined by following
    composite relations, possibly skipping specified entity types and/or
    relation types.
    """
    skiprtypes = set(skiprtypes).union((crtype, 'container_etype', 'container_parent'))
    skipetypes = set(skipetypes)
    subcontainers = set(subcontainers)
    etypes = set()
    rtypes = set()
    candidates = deque([schema[cetype]])
    while candidates:
        eschema = candidates.pop()
        if eschema.type in subcontainers:
            etypes.add(eschema.type)
            # however we stop right here as the subcontainer is responsible for
            # his own stuff
            continue
        for rschema, teschemas, role in eschema.relation_definitions():
            if rschema.meta or rschema in skiprtypes:
                continue
            if not composite_role(eschema, rschema) == role:
                continue
            if skipetypes.intersection(teschemas):
                continue
            rtypes.add(rschema.type)
            for teschema in teschemas:
                etype = teschema.type
                if etype not in etypes and etype not in skipetypes:
                    candidates.append(teschema)
                    etypes.add(etype)
    return frozenset(rtypes), frozenset(etypes)


@deprecated('[container 2.1] the container_parent hook is merged into another; '
            'please read the upgrade instructions')
def set_container_parent_rtypes_hook(schema, cetype, crtype, skiprtypes=(), skipetypes=(),
                                     subcontainers=()):
    """ etypes having several upward paths to the container have a dedicated container_parent
    rtype to speed up the parent computation
    this function computes the rtype set needed for the SetContainerParent hook selector
    """
    rtypes, etypes = container_static_structure(schema, cetype, crtype,
                                                skiprtypes=skiprtypes, skipetypes=skipetypes,
                                                subcontainers=subcontainers)
    select_rtypes = set()
    for etype in etypes:
        eschema = schema[etype]
        prschemas = list(parent_rschemas(eschema))
        if len(prschemas) > 1:
            for rschema, role in prschemas:
                if rschema.type in rtypes:
                    select_rtypes.add(rschema.type)
    return select_rtypes

def container_parent_rdefs(schema, cetype, crtype, skiprtypes=(), skipetypes=(),
                           subcontainers=()):
    """ etypes having several upward paths to the container have a dedicated container_parent
    rtype to speed up the parent computation

    usage:

      rdefs_select = container_parent_hook_selector(...)
      SetContainerRelation._container_parent_rdefs = rdefs_select
    """
    rtypes, etypes = container_static_structure(schema, cetype, crtype,
                                                skiprtypes=skiprtypes, skipetypes=skipetypes,
                                                subcontainers=subcontainers)
    select_rdefs = defaultdict(set)
    for etype in etypes:
        eschema = schema[etype]
        if not needs_container_parent(eschema):
            continue
        for rschema, role, teschema in parent_erschemas(eschema):
            if rschema.type in rtypes:
                if role == 'subject':
                    frometype, toetype = etype, teschema.type
                else:
                    frometype, toetype = teschema.type, etype
                select_rdefs[rschema.type].add((frometype, toetype))
    return dict(select_rdefs)


def set_container_relation_rtypes_hook(schema, cetype, crtype, skiprtypes=(), skipetypes=(),
                                       subcontainers=()):
    """computes the rtype set needed for etypes having just one upward
    path to the container, to be given to the SetContainerRealtion hook
    """
    rtypes, _etypes = container_static_structure(schema, cetype, crtype, skiprtypes, skipetypes,
                                                 subcontainers)
    return rtypes


def container_rtypes_etypes(schema, cetype, crtype, skiprtypes=(), skipetypes=(),
                            subcontainers=()):
    """Return all entity types and relation types that are part of the container.

    It extends ``container_static_structure`` with non structural relation types
    between entity types belonging to the defining structure of the container.
    """
    skiprtypes = set(skiprtypes).union((crtype,'container_etype', 'container_parent'))
    rtypes, etypes = container_static_structure(schema, cetype, crtype,
                                                skiprtypes, skipetypes, subcontainers)
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


def border_rtypes(schema, etypes, inner_rtypes):
    """ compute the set of rtypes that go from/to an etype in a container
    to/from an etype outside
    """
    META = cw_schema.META_RTYPES
    border_crossing = set()
    for etype in etypes:
        eschema = schema[etype]
        for rschema, _teschemas, _role in eschema.relation_definitions():
            if rschema.meta or rschema.final or rschema.type in META:
                continue
            if rschema.type in inner_rtypes:
                continue
            border_crossing.add(rschema.type)
    return border_crossing


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

# clone: fast eid range creation
@monkeypatch(NativeSQLSource)
def _create_eid_sqlite(self, session, count=1, eids=None):
    with self._eid_cnx_lock:
        eids = []
        for _x in xrange(count):
            for sql in self.dbhelper.sqls_increment_sequence('entities_id_seq'):
                cursor = self.doexec(session, sql)
            eids.append(cursor.fetchone()[0])
        if count > 1:
            return eids
        return eids[0]

@monkeypatch(NativeSQLSource)
def create_eid(self, session, count=1):
    with self._eid_cnx_lock:
        return self._create_eid(count)

@monkeypatch(NativeSQLSource)
def _create_eid(self, count, eids=None):
    # internal function doing the eid creation without locking.
    # needed for the recursive handling of disconnections (otherwise we
    # deadlock on self._eid_cnx_lock
    if self._eid_creation_cnx is None:
        self._eid_creation_cnx = self.get_connection()
    cnx = self._eid_creation_cnx
    try:
        eids = eids or []
        cursor = cnx.cursor()
        for _x in xrange(count):
            for sql in self.dbhelper.sqls_increment_sequence('entities_id_seq'):
                cursor.execute(sql)
            eids.append(cursor.fetchone()[0])
    except (self.OperationalError, self.InterfaceError):
        # FIXME: better detection of deconnection pb
        self.warning("trying to reconnect create eid connection")
        self._eid_creation_cnx = None
        return self._create_eid(count, eids)
    except self.DbapiError as exc:
        # We get this one with pyodbc and SQL Server when connection was reset
        if exc.args[0] == '08S01':
            self.warning("trying to reconnect create eid connection")
            self._eid_creation_cnx = None
            return self._create_eid(count, eids)
        else:
            raise
    except Exception:
        cnx.rollback()
        self._eid_creation_cnx = None
        self.exception('create eid failed in an unforeseen way on SQL statement %s', sql)
        raise
    else:
        cnx.commit()
        # one eid vs many
        # we must take a list because the postgres sequence does not
        # ensure a contiguous sequence
        if count > 1:
            return eids
        return eids[0]


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
        if needs_container_parent(eschema):
            for peschema in parent_eschemas(eschema):
                if (eschema, peschema) not in cparent.rdefs:
                    add_relation_definition(etype, 'container_parent', peschema.type)

    def unneeded_container_parent_rdefs():
        rdefs = []
        for subj, obj in cparent.rdefs:
            if not needs_container_parent(subj):
                rdefs.append((subj, obj))
        return rdefs

    for subj, obj in unneeded_container_parent_rdefs():
        drop_relation_definition(subj.type, 'container_parent', obj.type)
