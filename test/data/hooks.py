from cubicweb.server.hook import Hook, match_rtype
from cubes.container import hooks


def registration_callback(vreg):
    schema = vreg.schema
    rtypes_d, etypes_d = schema.container_static_structure('Diamond', 'diamond')
    rtypes_m, etypes_m = schema.container_static_structure('Mess', 'in_mess')
    hooks.SetContainerParent.__select__ = (Hook.__select__ &
                                           match_rtype(*rtypes_d.union(rtypes_m)))
