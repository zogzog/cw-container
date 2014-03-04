from cubicweb.server.hook import Hook, match_rtype
from cubes.container import hooks, utils, config


class SetCircusContainerRelation(hooks.SetContainerRelation):
    """Circus hook"""

class SetMenagerieContainerRelation(hooks.SetContainerRelation):
    """Menagerie hook"""

def registration_callback(vreg):
    schema = vreg.schema

    circus = config.Container.by_etype('Circus')
    rdefs = circus._container_parent_rdefs(schema)
    SetCircusContainerRelation._container_parent_rdefs = rdefs
    SetCircusContainerRelation.__select__ = Hook.__select__ & match_rtype(*circus.rtypes)
    vreg.register(SetCircusContainerRelation)


    menagerie = config.Container.by_etype('Menagerie')
    rdefs = menagerie._container_parent_rdefs(schema)
    SetMenagerieContainerRelation._container_parent_rdefs = rdefs
    SetMenagerieContainerRelation.__select__ = Hook.__select__ & match_rtype(*menagerie.rtypes)
    vreg.register(SetMenagerieContainerRelation)

