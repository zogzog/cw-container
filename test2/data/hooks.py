from cubes.container import config


def registration_callback(vreg):
    vreg.register(config.Container.container_hook())
