from warnings import warn
import logging
from collections import defaultdict, deque

from logilab.common.decorators import cachedproperty

from yams.buildobjs import RelationType, RelationDefinition

from cubicweb.predicates import is_instance
from cubicweb import schema as cw_schema

from cubes.container import utils


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

        self._protocol_adapter_cache = None
        self._schema = None

        if cetype in _CONTAINER_ETYPE_MAP:
            warn('Replacing existing container definition for %s' % cetype)
        _CONTAINER_ETYPE_MAP[cetype] = self

    @staticmethod
    def by_etype(cetype):
        return _CONTAINER_ETYPE_MAP.get(cetype)

    @staticmethod
    def all_etypes():
        return set(_CONTAINER_ETYPE_MAP.keys())

    def define_container(self, schema):
        """ Produce the necessary schema relations of a container:

        * (<container_rtype>, etype, cetype) for each container etype
        * (container_etype, etype, 'CWEType') for each container etype
        * an optional (if needed) (container_parent, etype, parent etype)
        """
        self._schema = schema

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


    def container_adapter(self, vreg):
        """ Return a subclass of the ContainerProtocol adapter with selector set """
        if self._protocol_adapter_cache is not None:
            return self._protocol_adapter_cache
        from cubes.container.entities import ContainerProtocol
        etypes = self.etypes
        # let's walk already registered containers to include *only* etypes
        # for which the adapter is not already defined
        for container in _CONTAINER_ETYPE_MAP.itervalues():
            if container._protocol_adapter_cache is not None:
                # a reasonnable thing to do is to not care if, for
                # some reason this container has no adapter set yet
                otheretypes = container.etypes
                etypes -= otheretypes
        # at this point, etypes may be an empty set, but
        # it should not really matter
        adapter = type(self.cetype + 'ContainerProtocol', (ContainerProtocol, ),
                       {'__select__': is_instance(*etypes)})
        self._protocol_adapter_cache = adapter
        vreg.register(adapter)
        return adapter

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
    def rtypes(self):
        """Return the set of all the structural rtypes included in the
        container (barring the <container_rtype>, container_etype and
        container_parent)

        NOTE: this is an imprecise set (e.g. some
        rtypes maye have rdefs actually completely out of the
        container) and you should ALWAYS prefer using `.rdefs`
        """
        rtypes = set()
        for rdef in self.rdefs:
            rtypes.add(rdef.rtype.type)
        return frozenset(rtypes)

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

    # /API
    # private methods

    def _container_parent_rdefs(self, schema):
        rtypes, etypes = self.rtypes, set(self.etypes)
        etypes.remove(self.cetype)
        select_rdefs = defaultdict(set)
        for etype in etypes:
            eschema = schema[etype]
            if not utils.needs_container_parent(eschema):
                continue
            for rschema, role, teschema in utils.parent_erschemas(eschema):
                if rschema.type in rtypes:
                    if role == 'subject':
                        frometype, toetype = etype, teschema.type
                    else:
                        frometype, toetype = teschema.type, etype
                    select_rdefs[rschema.type].add((frometype, toetype))
        return dict(select_rdefs)

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
