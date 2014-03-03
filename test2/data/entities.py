from cubicweb.selectors import is_instance

from cubes.container import utils, config
from cubes.container.entities import ContainerClone

class ProjectClone(ContainerClone):
    __select__ = is_instance('Project')


class FolderClone(ContainerClone):
    __select__ = is_instance('Folder')



def registration_callback(vreg):
    vreg.register_all(globals().values(), __name__)
    config.Container.by_etype('Project').container_adapter(vreg)
    config.Container.by_etype('Folder').container_adapter(vreg)
