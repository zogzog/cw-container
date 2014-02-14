from cubicweb.predicates import is_instance

from cubes.container import utils
from cubes.container.entities import Container, ContainerProtocol, ContainerClone


class Circus(Container):
    __regid__ = 'Circus'
    container_rtype = 'circus'
    container_subcontainers = ('Menagerie',)


class CProtocol(ContainerProtocol):
    """Circus protocol"""
    __select__ = is_instance('Circus')


class Menagerie(Container):
    __regid__ = 'Menagerie'
    container_rtype = 'zoo'


class MProtocol(ContainerProtocol):
    """Menagerie protocol"""
    __select__ = is_instance('Menagerie')


class CircusClone(ContainerClone):
    __select__ = is_instance('Circus')


class MenagerieClone(ContainerClone):
    __select__ = is_instance('Menagerie')


def registration_callback(vreg):
    vreg.register_all(globals().values(), __name__)
    _, etypes = utils.container_static_structure(vreg.schema, 'Circus', 'circus',
                                                 skipetypes=('Menagerie', ))
    CProtocol.__select__ = is_instance('Circus', *etypes)
