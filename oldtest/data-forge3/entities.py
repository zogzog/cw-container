from cubicweb.entities import AnyEntity

from config import PROJECT_CONTAINER, VERSION_CONTAINER

class Project(AnyEntity):
    __regid__ = 'Project'
    container_config = PROJECT_CONTAINER

class Version(AnyEntity):
    __regid__ = 'Version'
    container_config = VERSION_CONTAINER

def registration_callback(vreg):
    vreg.register_all(globals().values(), __name__)
    vreg.register(PROJECT_CONTAINER.build_container_protocol(vreg.schema))
    vreg.register(VERSION_CONTAINER.build_container_protocol(vreg.schema))
