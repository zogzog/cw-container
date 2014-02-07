from cubicweb.server.hook import Hook, match_rtype
from cubes.container import hooks, utils


class SetCircusContainerRelation(hooks.SetContainerRelation):
    """Circus hook"""


def registration_callback(vreg):
    schema = vreg.schema
    etype = 'Circus'
    eclass = vreg['etypes'].etype_class(etype)
    rdefs = utils.container_parent_rdefs(schema, etype,
                                         eclass.container_rtype,
                                         eclass.container_skiprtypes,
                                         eclass.container_skipetypes,
                                         eclass.container_subcontainers)
    SetCircusContainerRelation._container_parent_rdefs = rdefs
    rtypes = utils.set_container_relation_rtypes_hook(schema, etype,
                                                      eclass.container_rtype,
                                                      eclass.container_skiprtypes,
                                                      eclass.container_skipetypes,
                                                      eclass.container_subcontainers)
    SetCircusContainerRelation.__select__ = Hook.__select__ & match_rtype(*rtypes)
    vreg.register(SetCircusContainerRelation)

