from cubicweb.predicates import is_instance

from cubes.container import utils
from cubes.container.entities import (Container, ContainerProtocol,
                                      ContainerClone, MultiParentProtocol)

class Diamond(Container):
    __regid__ = 'Diamond'
    container_rtype = 'diamond'
    container_skipetypes = ('EtypeNotInContainers',)
    clone_rtype_role = ('is_clone_of', 'subject')


class DiamondClone(ContainerClone):
    rtypes_to_skip = ()
    etypes_to_skip = ()


class Mess(Container):
    __regid__ = 'Mess'
    container_rtype = 'in_mess'
    container_skiprtypes = ('local_group', 'wf_info_for')


class Multiparent(MultiParentProtocol):
    __select__ = is_instance('IAmAnAttributeCarryingRelation')


class CProtocol(ContainerProtocol):
    pass

def registration_callback(vreg):
    vreg.register(Diamond)
    vreg.register(DiamondClone)
    vreg.register(Mess)
    _rtypes, etypes_d = utils.container_static_structure(vreg.schema, 'Diamond', Diamond.container_rtype)
    _rtypes, etypes_m = utils.container_static_structure(vreg.schema, 'Mess', Mess.container_rtype)
    # let's add CWUser for tests
    CProtocol.__select__ = (ContainerProtocol.__select__ &
                            is_instance('CWUser', 'Diamond', 'Mess', *etypes_d.union(etypes_m)))
    vreg.register(CProtocol)
