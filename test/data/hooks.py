from config import DIAMOND_CONTAINER, MESS_CONTAINER


def registration_callback(vreg):
    for hook in (DIAMOND_CONTAINER.build_container_hooks(vreg.schema)
                 + MESS_CONTAINER.build_container_hooks(vreg.schema)):
        vreg.register(hook)
