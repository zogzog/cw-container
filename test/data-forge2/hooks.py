from cubicweb.server.hook import Hook, match_rtype
from cubes.container import hooks, utils

class SetProjectContainerRelation(hooks.SetContainerRelation):
    pass

class SetFolderContainerRelation(hooks.SetContainerRelation):
    pass


def registration_callback(vreg):
    schema = vreg.schema
    projeclass = vreg['etypes'].etype_class('Project')

    # Project definition
    rdefs = utils.container_parent_rdefs(schema, 'Project',
                                         projeclass.container_rtype,
                                         projeclass.container_skiprtypes,
                                         projeclass.container_skipetypes,
                                         projeclass.container_subcontainers)
    SetProjectContainerRelation._container_parent_rdefs = rdefs
    rtypes = utils.set_container_relation_rtypes_hook(schema, 'Project',
                                                      projeclass.container_rtype,
                                                      projeclass.container_skiprtypes,
                                                      projeclass.container_skipetypes,
                                                      projeclass.container_subcontainers)
    SetProjectContainerRelation.__select__ = Hook.__select__ & match_rtype(*rtypes)

    # Folder definition
    foldeclass = vreg['etypes'].etype_class('Folder')
    rdefs = utils.container_parent_rdefs(schema, 'Folder',
                                         foldeclass.container_rtype)
    SetFolderContainerRelation._container_parent_rdefs = rdefs
    rtypes = utils.set_container_relation_rtypes_hook(schema, 'Folder',
                                                      foldeclass.container_rtype)
    SetFolderContainerRelation.__select__ = (Hook.__select__ & match_rtype(*rtypes))

    vreg.register(SetProjectContainerRelation)
    vreg.register(SetFolderContainerRelation)
