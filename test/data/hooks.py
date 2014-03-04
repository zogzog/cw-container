from cubicweb.server.hook import match_rtype
from cubes.container import config, hooks


class CloneDiamond(hooks.CloneContainer):
    __select__ = hooks.CloneContainer.__select__ & match_rtype('is_clone_of')


def registration_callback(vreg):
    vreg.register(CloneDiamond)

    vreg.register(config.Container.container_hook())
