from cubicweb.server.hook import Hook, match_rtype
from cubes.container import hooks, utils


def registration_callback(vreg):
    schema = vreg.schema
    rtypes_d = utils.set_container_parent_rtypes_hook(schema, 'Diamond', 'diamond')
    rtypes_m = utils.set_container_parent_rtypes_hook(schema, 'Mess', 'in_mess')
    hooks.SetContainerParent.__select__ = (Hook.__select__ &
                                           match_rtype(*rtypes_d.union(rtypes_m)))
    rtypes_d = utils.set_container_relation_rtypes_hook(schema, 'Diamond', 'diamond')
    rtypes_m = utils.set_container_relation_rtypes_hook(schema, 'Mess', 'in_mess')
    hooks.SetContainerRelation.__select__ = (Hook.__select__ &
                                             match_rtype(*rtypes_d.union(rtypes_m)))
