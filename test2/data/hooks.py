from cubicweb.server.hook import Hook, match_rtype
from cubes.container import hooks, utils

class SetProjectContainerParent(hooks.SetContainerParent):
    __select__ = utils.yet_unset()

class SetProjectContainerRelation(hooks.SetContainerRelation):
    __select__ = utils.yet_unset()

class SetFolderContainerParent(hooks.SetContainerParent):
    __select__ = utils.yet_unset()

class SetFolderContainerRelation(hooks.SetContainerRelation):
    __select__ = utils.yet_unset()

def registration_callback(vreg):
    schema = vreg.schema
    projeclass = vreg['etypes'].etype_class('Project')

    # Project definition
    rtypes = utils.set_container_parent_rtypes_hook(schema, 'Project',
                                                    projeclass.container_rtype,
                                                    projeclass.container_skiprtypes,
                                                    projeclass.container_skipetypes,
                                                    projeclass.container_subcontainers)
    if rtypes:
        SetProjectContainerParent.__select__ = (Hook.__select__ & match_rtype(*rtypes))
        vreg.register(SetProjectContainerParent)
    rtypes = utils.set_container_relation_rtypes_hook(schema, 'Project',
                                                      projeclass.container_rtype,
                                                      projeclass.container_skiprtypes,
                                                      projeclass.container_skipetypes,
                                                      projeclass.container_subcontainers)
    if rtypes:
        SetProjectContainerRelation.__select__ = (Hook.__select__ & match_rtype(*rtypes))
        vreg.register(SetProjectContainerRelation)

    # Folder definition
    foldeclass = vreg['etypes'].etype_class('Folder')
    rtypes = utils.set_container_parent_rtypes_hook(schema, 'Folder',
                                                    foldeclass.container_rtype)
    if rtypes:
        SetFolderContainerParent.__select__ = (Hook.__select__ & match_rtype(*rtypes))
        vreg.register(SetFolderContainerParent)
    rtypes = utils.set_container_relation_rtypes_hook(schema, 'Folder',
                                                      foldeclass.container_rtype)
    if rtypes:
        SetFolderContainerRelation.__select__ = (Hook.__select__ & match_rtype(*rtypes))
        vreg.register(SetFolderContainerRelation)
