from warnings import warn

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

