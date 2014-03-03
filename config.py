from warnings import warn

from cubicweb.predicates import is_instance

from cubes.container import utils

_CONTAINER_ETYPE_MAP = {}


class Container(object):
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
        self.skiprtypes = skiprtypes
        self.skipetypes = skipetypes
        self.subcontainers = subcontainers
        self.clone_rtype_role = clone_rtype_role
        self.compulsory_hooks_categories = compulsory_hooks_categories

        self._protocol_adapter_cache = None

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
        utils.define_container(schema,
                               self.cetype,
                               self.crtype,
                               skiprtypes=self.skiprtypes,
                               skipetypes=self.skipetypes,
                               subcontainers=self.subcontainers)

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
        # let's walk already registered containers to include *only* etypes
        # for which the adapter is not already defined
        for container in _CONTAINER_ETYPE_MAP.itervalues():
            if container._protocol_adapter_cache is not None:
                # a reasonnable thing to do is to not care if, for
                # some reason this container has no adapter set yet
                structure = utils.container_static_structure
                _, otheretypes = structure(vreg.schema,
                                           self.cetype, self.crtype,
                                           skiprtypes=self.skiprtypes,
                                           skipetypes=self.skipetypes,
                                           subcontainers=self.subcontainers)
                etypes -= otheretypes
        # at this point, etypes may be an empty set, but
        # it should not really matter
        adapter = type(self.cetype + 'ContainerProtocol', (ContainerProtocol, ),
                       {'__select__': is_instance(self.cetype, *etypes)})
        self._protocol_adapter_cache = adapter
        vreg.register(adapter)
        return adapter

