from cubicweb.selectors import is_instance

from cubes.container.entities import ContainerClone

class ProjectClone(ContainerClone):
    __select__ = is_instance('Project')


class FolderClone(ContainerClone):
    __select__ = is_instance('Folder')

