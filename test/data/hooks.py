from cubicweb.server.hook import Hook, match_rtype
from cubes.container import hooks, utils, config

class SetDiamondContainerRelation(hooks.SetContainerRelation):
    pass

class SetMessContainerRelation(hooks.SetContainerRelation):
    pass


class CloneDiamond(hooks.CloneContainer):
    __select__ = hooks.CloneContainer.__select__ & match_rtype('is_clone_of')


def registration_callback(vreg):
    schema = vreg.schema
    diamond = config.Container.by_etype('Diamond')
    mess = config.Container.by_etype('Mess')
    rdefs = utils.container_parent_rdefs(schema,
                                         diamond.cetype,
                                         diamond.crtype,
                                         skiprtypes=diamond.skiprtypes,
                                         skipetypes=diamond.skipetypes)
    SetDiamondContainerRelation._container_parent_rdefs = rdefs

    rdefs = utils.container_parent_rdefs(schema,
                                         mess.cetype,
                                         mess.crtype,
                                         skipetypes=mess.skipetypes,
                                         skiprtypes=mess.skiprtypes)
    SetMessContainerRelation._container_parent_rdefs = rdefs

    rtypes = utils.set_container_relation_rtypes_hook(schema,
                                                      diamond.cetype,
                                                      diamond.crtype,
                                                      skipetypes=diamond.skipetypes)
    SetDiamondContainerRelation.__select__ = Hook.__select__ & match_rtype(*rtypes)

    rtypes = utils.set_container_relation_rtypes_hook(schema,
                                                      mess.cetype,
                                                      mess.crtype,
                                                      skiprtypes=mess.skiprtypes)
    SetMessContainerRelation.__select__ = Hook.__select__ & match_rtype(*rtypes)

    vreg.register(SetDiamondContainerRelation)
    vreg.register(SetMessContainerRelation)
    vreg.register(CloneDiamond)
