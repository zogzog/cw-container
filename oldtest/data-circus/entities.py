from cubicweb.predicates import is_instance
from cubicweb.entities import AnyEntity

from cubes.container.entities import ContainerClone

from config import CIRCUS_CONTAINER, MENAGERIE_CONTAINER


class Circus(AnyEntity):
    __regid__ = 'Circus'
    container_config = CIRCUS_CONTAINER


class Menagerie(AnyEntity):
    __regid__ = 'Menagerie'
    container_config = MENAGERIE_CONTAINER


class CircusClone(ContainerClone):
    __select__ = is_instance('Circus')


class MenagerieClone(ContainerClone):
    __select__ = is_instance('Menagerie')


def registration_callback(vreg):
    vreg.register_all(globals().values(), __name__)
    CIRCUS_CONTAINER.register_container_protocol(vreg)
    MENAGERIE_CONTAINER.register_container_protocol(vreg)
