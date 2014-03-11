from itertools import chain

from cubicweb.server import ON_COMMIT_ADD_RELATIONS

from config import PROJECT_CONTAINER, FOLDER_CONTAINER

def registration_callback(vreg):
    schema = vreg.schema
    for hookcls in PROJECT_CONTAINER.build_container_hooks(schema):
        vreg.register(hookcls)
    for hookcls in FOLDER_CONTAINER.build_container_hooks(schema):
        vreg.register(hookcls)
