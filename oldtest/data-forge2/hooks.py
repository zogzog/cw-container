
def registration_callback(vreg):
    from config import PROJECT_CONTAINER, FOLDER_CONTAINER
    PROJECT_CONTAINER.register_container_hooks(vreg)
    FOLDER_CONTAINER.register_container_hooks(vreg)
