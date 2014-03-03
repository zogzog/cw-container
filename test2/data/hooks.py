from cubicweb.server.hook import Hook, match_rtype
from cubes.container import hooks, utils, config

class SetProjectContainerRelation(hooks.SetContainerRelation):
    pass

class SetFolderContainerRelation(hooks.SetContainerRelation):
    pass


def registration_callback(vreg):
    schema = vreg.schema
    project = config.Container.by_etype('Project')

    # Project definition
    rdefs = project._container_parent_rdefs(schema)
    SetProjectContainerRelation._container_parent_rdefs = rdefs
    rtypes = utils.set_container_relation_rtypes_hook(schema,
                                                      project.cetype,
                                                      project.crtype,
                                                      skiprtypes=project.skiprtypes,
                                                      skipetypes=project.skipetypes,
                                                      subcontainers=project.subcontainers)
    SetProjectContainerRelation.__select__ = Hook.__select__ & match_rtype(*rtypes)

    # Folder definition
    folder = config.Container.by_etype('Folder')
    rdefs = folder._container_parent_rdefs(schema)

    SetFolderContainerRelation._container_parent_rdefs = rdefs
    rtypes = utils.set_container_relation_rtypes_hook(schema,
                                                      folder.cetype,
                                                      folder.crtype)
    SetFolderContainerRelation.__select__ = (Hook.__select__ & match_rtype(*rtypes))

    vreg.register(SetProjectContainerRelation)
    vreg.register(SetFolderContainerRelation)
