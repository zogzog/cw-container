from cubicweb.server.hook import Hook, match_rtype
from cubes.container import hooks, utils

class SetDiamondContainerRelation(hooks.SetContainerRelation):
    pass

class SetMessContainerRelation(hooks.SetContainerRelation):
    pass


def registration_callback(vreg):
    schema = vreg.schema
    rdefs = utils.container_parent_rdefs(schema, 'Diamond', 'diamond',
                                         skipetypes=('EtypeNotInContainers',))
    SetDiamondContainerRelation._container_parent_rdefs = rdefs

    rdefs = utils.container_parent_rdefs(schema, 'Mess', 'in_mess')
    SetMessContainerRelation._container_parent_rdefs = rdefs

    rtypes = utils.set_container_relation_rtypes_hook(schema, 'Diamond', 'diamond',
                                                      skipetypes=('EtypeNotInContainers',))
    SetDiamondContainerRelation.__select__ = Hook.__select__ & match_rtype(*rtypes)

    rtypes = utils.set_container_relation_rtypes_hook(schema, 'Mess', 'in_mess')
    SetMessContainerRelation.__select__ = Hook.__select__ & match_rtype(*rtypes)

    vreg.register(SetDiamondContainerRelation)
    vreg.register(SetMessContainerRelation)
