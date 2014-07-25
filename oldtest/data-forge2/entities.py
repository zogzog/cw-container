from cubicweb.predicates import is_instance
from cubicweb.entities import AnyEntity

from cubes.container.entities import ContainerClone

from config import PROJECT_CONTAINER, FOLDER_CONTAINER

class Project(AnyEntity):
    __regid__ = 'Project'
    container_config = PROJECT_CONTAINER


class Folder(AnyEntity):
    __regid__ = 'Folder'
    container_config = FOLDER_CONTAINER


class ProjectClone(ContainerClone):
    __select__ = is_instance('Project')


class FolderClone(ContainerClone):
    __select__ = is_instance('Folder')


def registration_callback(vreg):
    vreg.register_all(globals().values(), __name__)
    PROJECT_CONTAINER.register_container_protocol(vreg)
    FOLDER_CONTAINER.register_container_protocol(vreg)
