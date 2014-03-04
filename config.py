from warnings import warn
from collections import defaultdict, deque

from logilab.common.decorators import cachedproperty

from cubicweb.predicates import is_instance

from cubes.container import utils

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
        self._structure_cache = ((), ())
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
        self._schema = schema
        utils.define_container(schema,
                               self.cetype,
                               self.crtype,
                               skiprtypes=self.skiprtypes,
                               skipetypes=self.skipetypes,
                               subcontainers=self.subcontainers)

        # we're done, but also, warm the structure cache
        defstructure = utils.container_static_structure
        rtypes, etypes = defstructure(schema,
                                      self.cetype,
                                      self.crtype,
                                      skiprtypes=self.skiprtypes,
                                      skipetypes=self.skipetypes,
                                      subcontainers=self.subcontainers)
        self._structure_cache = rtypes, etypes

    def container_adapter(self, vreg):
        """ Return a subclass of the ContainerProtocol adapter with selector set """
        if self._protocol_adapter_cache is not None:
            return self._protocol_adapter_cache
        from cubes.container.entities import ContainerProtocol
        _, etypes = utils.container_static_structure(vreg.schema,
                                                     self.cetype,
                                                     self.crtype,
                                                     skiprtypes=self.skiprtypes,
                                                     skipetypes=self.skipetypes,
                                                     subcontainers=self.subcontainers)
        etypes = set(etypes)
        etypes.add(self.cetype)
        # let's walk already registered containers to include *only* etypes
        # for which the adapter is not already defined
        for container in _CONTAINER_ETYPE_MAP.itervalues():
            if container._protocol_adapter_cache is not None:
                # a reasonnable thing to do is to not care if, for
                # some reason this container has no adapter set yet
                _, otheretypes = container._structure_cache
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
        rdefs = set()
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
                    continue
                composite = utils.composite(rdef)
                component = utils.component(rdef)
                if eschema == composite:
                    rdefs.add(rdef)
                    if component in etypes or component in self.subcontainers:
                        continue
                    candidates.append(component)

        return rdefs

    # /API
    # private methods

    def _container_parent_rdefs(self, schema):
        rtypes, etypes = self._structure_cache
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
