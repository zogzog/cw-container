
def registration_callback(vreg):
    from config import CIRCUS_CONTAINER, MENAGERIE_CONTAINER
    CIRCUS_CONTAINER.register_container_hooks(vreg)
    MENAGERIE_CONTAINER.register_container_hooks(vreg)
