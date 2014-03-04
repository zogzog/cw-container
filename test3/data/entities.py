from cubicweb.predicates import is_instance

from cubes.container import utils, config
from cubes.container.entities import Container, ContainerProtocol, ContainerClone

class CircusClone(ContainerClone):
    __select__ = is_instance('Circus')


class MenagerieClone(ContainerClone):
    __select__ = is_instance('Menagerie')


def registration_callback(vreg):
    vreg.register_all(globals().values(), __name__)

    vreg.register(config.Container.container_adapter())
