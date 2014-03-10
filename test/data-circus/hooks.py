
from config import CIRCUS_CONTAINER, MENAGERIE_CONTAINER


def registration_callback(vreg):
    schema = vreg.schema
    for hookcls in CIRCUS_CONTAINER.build_container_hooks(schema):
        vreg.register(hookcls)
    for hookcls in MENAGERIE_CONTAINER.build_container_hooks(schema):
        vreg.register(hookcls)
