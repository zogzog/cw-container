
from config import CIRCUS_CONTAINER, MENAGERIE_CONTAINER


def registration_callback(vreg):
    schema = vreg.schema
    vreg.register(CIRCUS_CONTAINER.build_container_hook(schema))
    vreg.register(MENAGERIE_CONTAINER.build_container_hook(schema))
