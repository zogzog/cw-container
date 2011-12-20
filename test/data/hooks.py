from cubicweb.server.hook import Hook, match_rtype
from cubes.container import hooks, utils


def registration_callback(vreg):
    schema = vreg.schema
    rtypes_d, etypes_d = utils.container_static_structure(schema, 'Diamond', 'diamond')
    rtypes_m, etypes_m = utils.container_static_structure(schema, 'Mess', 'in_mess')
    hooks.SetContainerParent.__select__ = (Hook.__select__ &
                                           match_rtype(*rtypes_d.union(rtypes_m)))
