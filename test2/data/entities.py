from cubicweb.selectors import is_instance

from cubes.container import utils
from cubes.container.entities import Container, ContainerProtocol, MultiParentProtocol

class Project(Container):
    __regid__ = 'Project'
    container_rtype = 'project'

def registration_callback(vreg):
    vreg.register(Project)
    _rtypes, etypes = utils.container_static_structure(vreg.schema, 'Project', Project.container_rtype)
    ContainerProtocol.__select__ = (ContainerProtocol.__select__ &
                                    is_instance('Project', *etypes))
