from cubicweb.predicates import is_instance

from cubes.container import utils, config
from cubes.container.entities import Container, ContainerProtocol, ContainerClone

class CircusClone(ContainerClone):
    __select__ = is_instance('Circus')


class MenagerieClone(ContainerClone):
    __select__ = is_instance('Menagerie')


def registration_callback(vreg):
    vreg.register_all(globals().values(), __name__)

    circus = config.Container.by_etype('Circus')
    circus.container_adapter(vreg)
    menagerie = config.Container.by_etype('Menagerie')
    menagerie.container_adapter(vreg)
