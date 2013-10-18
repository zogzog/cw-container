from cubicweb.selectors import is_instance

from cubes.container import utils
from cubes.container.entities import Container, ContainerProtocol, ContainerClone

class Project(Container):
    __regid__ = 'Project'
    container_rtype = 'project'
    container_subcontainers = ('Folder',)


class ProjectClone(ContainerClone):
    __select__ = is_instance('Project')


class Folder(Container):
    __regid__ = 'Folder'
    container_rtype = 'folder_root'


class FolderClone(ContainerClone):
    __select__ = is_instance('Folder')


def registration_callback(vreg):
    vreg.register_all(globals().values(), __name__)
    _rtypes, proj_etypes = utils.container_static_structure(vreg.schema, 'Project',
                                                            Project.container_rtype,
                                                            subcontainers=Project.container_subcontainers)
    _rtypes, fold_etypes = utils.container_static_structure(vreg.schema, 'Folder', Folder.container_rtype)
    Container.__select__ = is_instance('Project', *(proj_etypes | fold_etypes))
