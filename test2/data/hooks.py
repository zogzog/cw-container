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
    SetProjectContainerRelation.__select__ = Hook.__select__ & match_rtype(*project.rtypes)

    # Folder definition
    folder = config.Container.by_etype('Folder')
    rdefs = folder._container_parent_rdefs(schema)

    SetFolderContainerRelation._container_parent_rdefs = rdefs
    SetFolderContainerRelation.__select__ = (Hook.__select__ & match_rtype(*folder.rtypes))

    vreg.register(SetProjectContainerRelation)
    vreg.register(SetFolderContainerRelation)
