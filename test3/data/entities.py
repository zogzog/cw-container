from cubicweb.predicates import is_instance

from cubes.container import utils
from cubes.container.entities import Container, ContainerProtocol


class Circus(Container):
    __regid__ = 'Circus'
    container_rtype = 'circus'


class CProtocol(ContainerProtocol):
    """Circus protocol"""


def registration_callback(vreg):
    vreg.register_all(globals().values(), __name__)
    _, etypes = utils.container_static_structure(vreg.schema, 'Circus', 'circus')
    CProtocol.__select__ = is_instance('Circus', *etypes)
