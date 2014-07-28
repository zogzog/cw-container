from cubicweb.predicates import is_instance

from cubes.container.entities import ContainerClone

class CircusClone(ContainerClone):
    __select__ = is_instance('Circus')


class MenagerieClone(ContainerClone):
    __select__ = is_instance('Menagerie')

