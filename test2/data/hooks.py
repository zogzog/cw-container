from cubicweb.server.hook import Hook, match_rtype
from cubes.container import hooks, utils

class SetContainerParent(hooks.SetContainerParent):
    __select__ = utils.yet_unset()

class SetContainerRelation(hooks.SetContainerRelation):
    __select__ = utils.yet_unset()


def registration_callback(vreg):
    schema = vreg.schema
    rtypes = utils.set_container_parent_rtypes_hook(schema, 'Project', 'project')
    if rtypes:
        SetContainerParent.__select__ = (Hook.__select__ & match_rtype(*rtypes))
    rtypes = utils.set_container_relation_rtypes_hook(schema, 'Project', 'project')
    SetContainerRelation.__select__ = (Hook.__select__ & match_rtype(*rtypes))
    vreg.register(SetContainerParent)
    vreg.register(SetContainerRelation)
