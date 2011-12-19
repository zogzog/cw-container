from cubicweb.selectors import is_instance
from cubes.container.entities import Container, ContainerProtocol, MultiParentProtocol

class Diamond(Container):
    __regid__ = 'Diamond'
    container_rtype = 'diamond'

class Mess(Container):
    __regid__ = 'Mess'
    container_rtype = 'in_mess'
    container_skiprtypes = ('local_group',)

def registration_callback(vreg):
    vreg.register(Diamond)
    vreg.register(Mess)
    _rtypes, etypes_d = vreg.schema.container_static_structure('Diamond', Diamond.container_rtype)
    _rtypes, etypes_m = vreg.schema.container_static_structure('Mess', Mess.container_rtype)
    ContainerProtocol.__select__ = (ContainerProtocol.__select__ &
                                    is_instance('Diamond', 'Mess', *etypes_d.union(etypes_m)))
    MultiParentProtocol.__select__ = is_instance('IAmAnAttributeCarryingRelation')
