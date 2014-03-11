from cubicweb.entities import AnyEntity

from cubicweb.predicates import is_instance

from cubes.container import utils
from cubes.container.entities import (Container, ContainerProtocol,
                                      ContainerClone, MultiParentProtocol)

from config import DIAMOND_CONTAINER, MESS_CONTAINER


class Diamond(AnyEntity):
    __regid__ = 'Diamond'
    container_config = DIAMOND_CONTAINER


class DiamondClone(ContainerClone):
    __select__ = is_instance('Diamond')


class Mess(AnyEntity):
    __regid__ = 'Mess'
    container_config = MESS_CONTAINER


class MessClone(ContainerClone):
    __select__ = is_instance('Mess')



def registration_callback(vreg):
    vreg.register_all(globals().values(), __name__)
    vreg.register(DIAMOND_CONTAINER.build_container_protocol(vreg.schema))
    vreg.register(MESS_CONTAINER.build_container_protocol(vreg.schema))
