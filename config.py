from warnings import warn
import logging
from collections import defaultdict, deque

from logilab.common.decorators import cachedproperty

from yams.buildobjs import RelationType, RelationDefinition

from cubicweb import schema as cw_schema
from cubicweb.predicates import is_instance
from cubicweb.server import ON_COMMIT_ADD_RELATIONS

from cubes.container import utils
from cubes.container.secutils import PERM, PERMS


logger = logging.getLogger('cubes.container')

_CONTAINER_ETYPE_MAP = {}


class Container(object):
    # API
    cetype = None
    crtype = None
    skiprtypes = ()
    skipetypes = ()
    subcontainers = ()
    clone_rtype_role = None
    compulsory_hooks_categories = ()

    def __init__(self,
                 cetype,
                 crtype,
                 skiprtypes=(),
                 skipetypes=(),
                 subcontainers=(),
                 clone_rtype_role=None,
                 compulsory_hooks_categories=()):

        self.cetype = cetype
        self.crtype = crtype
        self.skiprtypes = set(skiprtypes)
        self.skipetypes = set(skipetypes)
        self.subcontainers = set(subcontainers)
        self.clone_rtype_role = clone_rtype_role
        self.compulsory_hooks_categories = compulsory_hooks_categories

        self._schema = None

        if cetype in _CONTAINER_ETYPE_MAP:
            warn('Replacing existing container definition for %s' % cetype)
        _CONTAINER_ETYPE_MAP[cetype] = self

    def __str__(self):
        return '<Container(%s)>' % self.cetype
    __repr__ = __str__

    @staticmethod
    def by_etype(cetype):
        return _CONTAINER_ETYPE_MAP.get(cetype)

    @staticmethod
    def all_etypes():
        return set(_CONTAINER_ETYPE_MAP.keys())

    # setup methods

    def define_container(self, schema):
        """ Produce the necessary schema relations of a container:

        * (<container_rtype>, etype, cetype) for each container etype
        * (container_etype, etype, 'CWEType') for each container etype
        * an optional (if needed) (container_parent, etype, parent etype)
        """
        self._schema = schema
        if not utils.fsschema(schema):
            logger.info('define_container: this is a repo schema, nothing to do')
            return

        if not self.crtype in schema:
            # ease pluggability of container in existing applications
            schema.add_relation_type(RelationType(self.crtype, inlined=True))
            cw_schema.META_RTYPES.add(self.crtype)
        else:
            logger.warning('%r is already defined in the schema - you probably want '
                           'to let it to the container cube', self.crtype)
        crschema = schema[self.crtype]
        cetype_rschema = schema['container_etype']

        for etype in self.etypes:

            # populate <container_rtype>
            if (etype, self.cetype) not in crschema.rdefs:
                # checking this will help adding containers to existing applications
                # and reusing the container rtype
                schema.add_relation_def(RelationDefinition(etype,
                                                           self.crtype,
                                                           self.cetype,
                                                           cardinality='?*'))
            else:
                logger.warning('%r - %r - %r rdef is already defined in the schema '
                               '- you probably want to let it to the container cube',
                               etype, self.crtype, self.cetype)

            # populate container_etype
            if (etype, 'CWEType') not in cetype_rschema.rdefs:
                schema.add_relation_def(RelationDefinition(etype,
                                                           'container_etype',
                                                           'CWEType',
                                                           cardinality='?*'))

            # populate container_parent
            eschema = schema[etype]
            if utils.needs_container_parent(eschema):
                cparent_rschema = schema['container_parent']
                for peschema in utils.parent_eschemas(eschema):
                    petype = peschema.type
                    if (etype, petype) in cparent_rschema.rdefs:
                        continue
                    schema.add_relation_def(RelationDefinition(etype,
                                                               'container_parent',
                                                               petype,
                                                               cardinality='?*'))


    @classmethod
    def container_adapters(cls):
        """Return a concrete subclass of the ContainerProtocol adapter with
        selector set for *all* the containers
        """
        from cubes.container.entities import ContainerProtocol, ContainerClone
        cetypes = []
        etypes = set()
        for container in _CONTAINER_ETYPE_MAP.itervalues():
            cetypes.append(container.cetype)
            etypes |=  container.etypes
        prefix = ''.join(cetypes)
        cpadapter = type(prefix + 'ContainerProtocol', (ContainerProtocol,), {})
        cpadapter.__select__ = is_instance(*etypes)
        ccadapter = type(prefix + 'ContainerClone', (ContainerClone,), {})
        ccadapter.__select__ = is_instance(*etypes)
        return (cpadapter, ccadapter)

    @classmethod
    def container_hooks(cls):
        """Return concrete subclasses of the SetContainerRelation hook with
        selector set for *all* the containers and the NewContainer
        hook with selector set for each container type.
        """
        from cubes.container.hooks import SetContainerRelation, NewContainer, match_rdefs
        cetypes = []
        rdefs = set()
        parentrdefs = defaultdict(set)
        for container in _CONTAINER_ETYPE_MAP.itervalues():
            cetypes.append(container.cetype)
            rdefs |=  container.rdefs
            for rtype, from_to in container._container_parent_rdefs.iteritems():
                parentrdefs[rtype] |= from_to
        prefix = ''.join(cetypes)
        setrelationhook = type(prefix + 'ContainerRelationHook',
                               (SetContainerRelation,),
                               {'__select__': match_rdefs(*rdefs),
                                '__registry__': 'after_add_relation_hooks',
                                '_container_parent_rdefs': parentrdefs})
        newcontainerhook = type(prefix + 'NewContainer',
                                (NewContainer,),
                                {'__select__': is_instance(*cetypes),
                                 '__registry__': 'after_add_entity_hooks'})
        return (setrelationhook, newcontainerhook)

    def setup_etypes_security(self, etype_perms):
        """Automatically decorate the etypes with the given permission rules,
        which must be a normal permissions dictionary.

        """
        if (not utils.fsschema(self._schema) or
            getattr(self._schema, '_etypes_%s_security' % self.cetype, False)):
            return
        assert isinstance(etype_perms, dict)
        for etype in self.etypes:
            eschema = self._schema[etype]
            if isinstance(eschema.permissions, PERM):
                eschema.permissions = PERMS[eschema.permissions]
            else:
                eschema.permissions = etype_perms
        setattr(self._schema, '_etypes_%s_security' % self.cetype, True)

    def setup_rdefs_security(self, inner_rdefs_perms, border_rdefs_perms=None):
        """Automatically decorate the inner rdefs and border rdefs with the
        given permission rules.

        Either inner_rdefs_perms or border_rdefs_perms can be:

        * a plain dictionary (to feed immediately to rdef.__permissions__),

        * a function taking a string valued to 'S' or 'O' indicating
          the direction of the container, for use in RRQLExpressions,
          and returning a permissions dict.

        For those rdefs that have been statically decorated with a
        PERM tag, the matching permission dict will be fetched from
        the PERMS dictionary, e.g.::

          PERMS['allowed-if-open-state'] = {
              'read':   ('managers', 'users'),
              'add':    ('managers', RRQLExpression('X in_state S, S name "open"')),
              'delete': ('managers', RRQLExpression('X in_state S, S name "open"'))
          }

          class done_in_version(RelationDefinition):
              __permissions__ = PERM('allowed-if-open-state')

        """
        if (not utils.fsschema(self._schema) or
            getattr(self._schema, '_rdefs_%s_security' % self.cetype, False)):
            return

        processed_permission_rdefs = set()

        def role_to_container(rdef, rdef_role):
            """ computes a mapping of (subjet, object) to 'S' or 'O' role name
            giving the direction of the container root
            """
            if rdef.composite is None:
                # if both the subj/obj are in the container, we
                # default to the subject (it does not really matter)
                if rdef.subject.type in self.etypes:
                    rdef_role[rdef] = 'S'
                elif rdef.object.type in self.etypes:
                    rdef_role[rdef] = 'O'

                return
            # structural relations:
            # we must choose the side nearest to the container root
            # 'subject' => 'S', 'object' => 'O'
            # Both subj/obj must be in etypes
            # This should be true here
            assert rdef.subject in self.etypes or rdef.object in self.etypes

            composite = utils.composite(rdef)
            # filter out subcontainer
            # any relation who defined a subcontainer as a composite
            # is not ours and its handling will be delegated
            # ... but take care of recursive containers
            if composite in self.subcontainers and composite != self.cetype:
                return

            # any relation that points to an etype which is not ours
            # will be handled by someone else
            if composite not in self.etypes:
                return

            rdef_role[rdef] = rdef.composite[:1].upper()

        def set_rdefs_perms(rdefs_roles, perms, processed):
            """ for all collected rdefs, set the permissions
            * using the specially tagged PERM object
            * using the perms('S' or 'O') callable
            * using a plain normal permission dict
            """
            assert callable(perms) or isinstance(perms, dict) or perms is None
            for rdef, role in rdefs_roles.iteritems():
                if rdef in processed:
                    continue
                if isinstance(rdef.permissions, PERM):
                    rdef.permissions = PERMS[rdef.permissions]
                elif isinstance(perms, dict):
                    rdef.permissions = perms
                elif callable(perms):
                    rdef.permissions = perms(role)
                assert not callable(rdef.permissions), rdef.permissions
                processed.add(rdef)

        # 1. internal rtypes
        rdef_role = {}
        for rdef in self.rdefs:
            ON_COMMIT_ADD_RELATIONS.add(rdef.rtype.type)
            role_to_container(rdef, rdef_role)
        set_rdefs_perms(rdef_role, inner_rdefs_perms, processed_permission_rdefs)

        # 2. border crossing rtypes
        rdef_role = {}
        for rdef in sorted(self.border_rdefs):
            ON_COMMIT_ADD_RELATIONS.add(rdef.rtype.type)
            role_to_container(rdef, rdef_role)
        set_rdefs_perms(rdef_role, border_rdefs_perms, processed_permission_rdefs)

        setattr(self._schema, '_rdefs_%s_security' % self.cetype, True)

    # /setup
    # container accessors

    @cachedproperty
    def rdefs(self):
        """Return the rdefs that define the structure of the container. """
        assert self._schema, 'did you call .define_container ?'
        skiprtypes = self.skiprtypes | set((self.crtype, 'container_etype', 'container_parent'))
        structuralrdefs = set()
        otherrdefs = set()
        etypes = set()
        candidates = deque([self._schema[self.cetype]])
        while candidates:
            eschema = candidates.pop()
            etypes.add(eschema.type)
            for rdef in utils.iterrdefs(eschema,
                                        meta=False,
                                        final=False,
                                        skiprtypes=skiprtypes,
                                        skipetypes=self.skipetypes):

                if rdef.composite is None:
                    otherrdefs.add(rdef)
                    continue

                composite = utils.composite(rdef)
                component = utils.component(rdef)

                if eschema == composite:
                    structuralrdefs.add(rdef)
                    if (component in etypes or             # already seen
                        component in self.subcontainers):  # delegated
                        continue
                    candidates.append(component)

        # this will simplify a lot .inner_rdefs computation
        self._pendingrdefs = otherrdefs

        return frozenset(structuralrdefs)

    @cachedproperty
    def inner_rdefs(self):
        """Return all the rdefs that belong to the container including
        structural rdefs
        """
        rdefs = set(self.rdefs) # ensure we have ._pendingrdefs
        etypes = self.etypes
        skiprtypes = set()
        if self.clone_rtype_role:
            skiprtypes.add(self.clone_rtype_role[0])
        for rdef in self._pendingrdefs:
            if rdef.rtype.type in skiprtypes:
                continue
            if rdef.subject in etypes and rdef.object in etypes:
                rdefs.add(rdef)

        return frozenset(rdefs)

    @cachedproperty
    def border_rdefs(self):
        """ compute the set of rtypes that go from/to an etype in a container
        to/from an etype outside """
        excluderdefs = self.inner_rdefs
        for cetype in self.subcontainers:
            # we exclude the border_rdefs from the subcontainers
            if cetype == self.cetype:
                # self-recursive container, only the top-level is a security scope
                continue
            subconf = self.by_etype(cetype)
            assert subconf is not None, ('You must register the %s subcontainer before '
                                         'calling .border_rdefs' % cetype)
            excluderdefs |= subconf.border_rdefs
            excluderdefs |= subconf.inner_rdefs
        border_crossing = set()
        for etype in self.etypes:
            eschema = self._schema[etype]
            for rdef in utils.iterrdefs(eschema, meta=False, final=False,
                                        skiprtypes=self.skiprtypes,
                                        skipetypes=self.skipetypes):
                if rdef in excluderdefs:
                    continue
                border_crossing.add(rdef)
        return border_crossing

    @cachedproperty
    def etypes(self):
        """Return the set of all the etypes belonging to the container
        (including the container etype itself)
        """
        etypes = set()
        for rdef in self.rdefs:
            etypes.add(rdef.subject.type)
            etypes.add(rdef.object.type)
        return frozenset(etypes)

    @cachedproperty
    def ordered_etypes(self):
        """Return list of etypes of a container by dependency order this is
        provided for simplicity and backward compatibility reasons.

        Etypes that are parts of a cycle are undiscriminately added at
        the end.
        """
        orders, etype_map = self._container_etype_orders()
        total_order = []
        for order in orders:
            total_order += order
        return total_order + etype_map.keys()

    # /accessors
    # /API

    # private methods

    @cachedproperty
    def _container_parent_rdefs(self):
        """Compute a mapping from rtype to subject/object for use by the
        container hook. The hook will notice when the from/to etypes
        are in this mapping and compute the effective container_parent
        relation.
        """
        cprdefs = defaultdict(set)
        inner_rdefs = self.inner_rdefs
        for etype in self.etypes:
            eschema = self._schema[etype]
            if not utils.needs_container_parent(eschema):
                continue
            # let's compute the parent rdefs of this container
            for parent_rdef in utils.parent_rdefs(eschema):
                if parent_rdef not in inner_rdefs:
                    continue
                cprdefs[parent_rdef.rtype.type].add((parent_rdef.subject.type,
                                                     parent_rdef.object.type))
        return dict(cprdefs)

    def _needed_etypes(self, etype):
        """Finds all container etypes this one depends on to be built start
        from all subject + object relations
        """
        etypes = defaultdict(list)
        # skipetypes = set((cetype,))
        # these should include rtypes
        # that create cycles but actually are false dependencies
        skiprtypes = set((self.crtype, 'container_etype', 'container_parent'))
        eschema = self._schema[etype]
        adjacent_rschemas = [(rschema, role)
                             for role in ('subject', 'object')
                             for rschema in getattr(eschema, '%s_relations' % role)()
                             if not (rschema.meta or rschema.final or rschema.type in skiprtypes)]
        children_rtypes = [r.type for r in utils.children_rschemas(eschema)]
        parent_etypes = set(utils.parent_eschemas(eschema))
        for rschema, role in adjacent_rschemas:
            if rschema in children_rtypes:
                # we shouldn't depend from our children ...
                continue
            for rdef in rschema.rdefs.values():
                target = getattr(rdef, utils.neg_role(role))
                if target.type in self.skipetypes:
                    continue
                if target.type not in parent_etypes:
                    # an inner not-parent, not-children relation
                    if rdef.cardinality[0 if role == 'subject' else 1] in '?*':
                        continue # this is a soft dependency
                # what shoulld be left is either entities bound by '1+' cardinalities
                # or parent entities
                etypes[target.type].append((rdef, role))
        return etypes

    def _container_etype_orders(self):
        """Computes linearizations and cycles of etypes within a container"""
        etypes = set(self.etypes)
        orders = []
        etype_map = dict((etype, self._needed_etypes(etype))
                         for etype in etypes)
        maplen = len(etype_map)
        while etype_map:
            neworder = utils.linearize(etype_map, etypes)
            if neworder:
                orders.append(neworder)
            if maplen == len(etype_map):
                break
            maplen = len(etype_map)
        return orders, etype_map
