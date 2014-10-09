from cubicweb.entities import AnyEntity

from config import PROJECT_CONTAINER

class Project(AnyEntity):
    __regid__ = 'Project'
    container_config = PROJECT_CONTAINER

def registration_callback(vreg):
    vreg.register_all(globals().values(), __name__)
    PROJECT_CONTAINER.register_container_protocol(vreg)
