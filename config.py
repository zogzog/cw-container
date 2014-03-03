


class Container(object):
    cetype = None
    crtype = None
    skiprtypes = ()
    skipetypes = ()
    subcontainers = ()
    compulsory_hooks_categories = ()

    def __init__(self,
                 cetype,
                 crtype,
                 skiprtypes=(),
                 skipetypes=(),
                 subcontainers=(),
                 compulsory_hooks_categories=()):

        self.cetype = cetype
        self.crtype = crtype
        self.skiprtypes = skiprtypes
        self.skipetypes = skipetypes
        self.subcontainers = subcontainers
        self.compulsory_hooks_categories = compulsory_hooks_categories


