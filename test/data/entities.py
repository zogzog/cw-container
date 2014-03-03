from cubicweb.predicates import is_instance

from cubes.container import utils, config
from cubes.container.entities import (Container, ContainerProtocol,
                                      ContainerClone, MultiParentProtocol)

class DiamondClone(ContainerClone):
    rtypes_to_skip = ()
    etypes_to_skip = ()

class Multiparent(MultiParentProtocol):
    __select__ = is_instance('IAmAnAttributeCarryingRelation')


class CProtocol(ContainerProtocol):
    pass

def registration_callback(vreg):
    vreg.register(DiamondClone)
    diamond = config.Container.by_etype('Diamond')
    mess = config.Container.by_etype('Mess')
    _rtypes, etypes_d = utils.container_static_structure(vreg.schema, diamond.cetype, diamond.crtype,
                                                         skipetypes=diamond.skipetypes)
    _rtypes, etypes_m = utils.container_static_structure(vreg.schema, mess.cetype, mess.crtype,
                                                         skiprtypes=mess.skiprtypes)
    # let's add CWUser for tests
    CProtocol.__select__ = (ContainerProtocol.__select__ &
                            is_instance('CWUser', 'Diamond', 'Mess', *etypes_d.union(etypes_m)))
    vreg.register(CProtocol)
