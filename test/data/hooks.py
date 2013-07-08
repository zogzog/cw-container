from cubicweb.server.hook import Hook, match_rtype
from cubes.container import hooks, utils

class SetContainerParent(hooks.SetContainerParent):
    __select__ = utils.yet_unset()

class SetContainerRelation(hooks.SetContainerRelation):
    __select__ = utils.yet_unset()


def registration_callback(vreg):
    schema = vreg.schema
    rtypes_d = utils.set_container_parent_rtypes_hook(schema, 'Diamond', 'diamond',
                                                      skipetypes=('EtypeNotInContainers',))
    rtypes_m = utils.set_container_parent_rtypes_hook(schema, 'Mess', 'in_mess')
    SetContainerParent.__select__ = (Hook.__select__ &
                                     match_rtype(*rtypes_d.union(rtypes_m)))
    rtypes_d = utils.set_container_relation_rtypes_hook(schema, 'Diamond', 'diamond',
                                                        skipetypes=('EtypeNotInContainers',))
    rtypes_m = utils.set_container_relation_rtypes_hook(schema, 'Mess', 'in_mess')
    SetContainerRelation.__select__ = (Hook.__select__ &
                                       match_rtype(*rtypes_d.union(rtypes_m)))
    vreg.register(SetContainerParent)
    vreg.register(SetContainerRelation)
