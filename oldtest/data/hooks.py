
def registration_callback(vreg):
    from config import DIAMOND_CONTAINER, MESS_CONTAINER
    DIAMOND_CONTAINER.register_container_hooks(vreg)
    MESS_CONTAINER.register_container_hooks(vreg)
