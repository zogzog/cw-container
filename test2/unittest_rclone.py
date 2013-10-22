from logilab.common.testlib import unittest_main

from cubicweb import Binary, ValidationError
from cubicweb.devtools.testlib import CubicWebTC

from cubes.container import utils
from cubes.container.testutils import userlogin, new_version, new_ticket, new_patch


class TwoContainersTC(CubicWebTC):

    # Project
    def test_project_static_structure(self):
        schema = self.vreg.schema
        project = self.vreg['etypes'].etype_class('Project')
        self.assertEqual((frozenset(['documents', 'implements', 'concerns', 'version_of', 'subproject_of']),
                          frozenset(['Patch', 'Ticket', 'Version', 'Folder','Project'])),
                         utils.container_static_structure(schema, 'Project', 'project',
                                                          skiprtypes=project.container_skiprtypes,
                                                          skipetypes=project.container_skipetypes,
                                                          subcontainers=project.container_subcontainers))


    def test_project_etypes_rtypes(self):
        schema = self.vreg.schema
        project = self.vreg['etypes'].etype_class('Project')
        # NOTE: this contains 'parent', which is WRONG
        # However, short of fully specifying the subcontainer (not just the top entity type)
        # we cannot do much against that. We really need some support viz Yams
        # (e.g. http://www.logilab.org/ticket/100723)
        self.assertEqual((frozenset(['implements', 'documents', 'parent', 'done_in_version',
                                     'concerns', 'version_of', 'subproject_of']),
                          frozenset(['Folder', 'Patch', 'Ticket', 'Version', 'Project'])),
                         utils.container_rtypes_etypes(schema, 'Project', 'project',
                                                       skiprtypes=project.container_skiprtypes,
                                                       skipetypes=project.container_skipetypes,
                                                       subcontainers=project.container_subcontainers))


    def test_project_hooks(self):
        schema = self.vreg.schema
        project = self.vreg['etypes'].etype_class('Project')
        self.assertEqual(set(['documents']),
                         utils.set_container_parent_rtypes_hook(schema, 'Project', 'project',
                                                                  skiprtypes=project.container_skiprtypes,
                                                                  skipetypes=project.container_skipetypes,
                                                                  subcontainers=project.container_subcontainers))
        self.assertEqual(set(['implements', 'concerns', 'version_of', 'subproject_of']),
                         utils.set_container_relation_rtypes_hook(schema, 'Project', 'project',
                                                                  skiprtypes=project.container_skiprtypes,
                                                                  skipetypes=project.container_skipetypes,
                                                                  subcontainers=project.container_subcontainers))

    # Folder
    def test_folder_static_structure(self):
        schema = self.vreg.schema
        folder = self.vreg['etypes'].etype_class('Folder')
        self.assertEqual((frozenset(['parent', 'element']),
                          frozenset(['Folder', 'File'])),
                         utils.container_static_structure(schema, 'Folder', 'folder_root',
                                                          skiprtypes=folder.container_skiprtypes,
                                                          skipetypes=folder.container_skipetypes))

    def test_folder_etypes_rtypes(self):
        schema = self.vreg.schema
        folder = self.vreg['etypes'].etype_class('Folder')
        self.assertEqual((frozenset(['parent', 'element']),
                          frozenset(['Folder', 'File'])),
                         utils.container_rtypes_etypes(schema, 'Folder', 'folder_root',
                                                       skiprtypes=folder.container_skiprtypes,
                                                       skipetypes=folder.container_skipetypes))

    def test_folder_hooks(self):
        schema = self.vreg.schema
        folder = self.vreg['etypes'].etype_class('Folder')
        self.assertEqual(set(['parent']),
                         utils.set_container_parent_rtypes_hook(schema, 'Folder', 'folder_root',
                                                                  skiprtypes=folder.container_skiprtypes,
                                                                  skipetypes=folder.container_skipetypes,
                                                                  subcontainers=folder.container_subcontainers))
        self.assertEqual(set(['element']),
                         utils.set_container_relation_rtypes_hook(schema, 'Folder', 'folder_root',
                                                                  skiprtypes=folder.container_skiprtypes,
                                                                  skipetypes=folder.container_skipetypes,
                                                                  subcontainers=folder.container_subcontainers))

def parent_titles(parent):
    parents = []
    while True:
        parent = parent.cw_adapt_to('Container').parent
        if parent is None:
            break
        parents.append(parent.dc_title())
    return parents

class CloneTC(CubicWebTC):
    userlogin = userlogin

    def setup_database(self):
        req = self.request()
        proj = req.create_entity('Project', name=u'Babar')
        projeid = req.execute('Project P').get_entity(0, 0)
        ver = new_version(req, projeid)
        tick = new_ticket(req, projeid, ver)
        afile = req.create_entity('File', data=Binary('foo'))
        patch = new_patch(req, tick, afile)

        doc1 = req.create_entity('File', data=Binary('How I became King'))
        fold1 = req.create_entity('Folder', name=u'Babar documentation',
                                  element=doc1, documents=projeid)

        # a subproject
        proj = req.create_entity('Project', name=u'Celeste',
                                 subproject_of=proj)
        projeid = proj.eid
        ver = new_version(req, projeid)
        tick = new_ticket(req, projeid, ver, name=u'write bio', descr=u'do it')
        afile = req.create_entity('File', data=Binary('foo'))
        patch = new_patch(req, tick, afile, name=u'bio part one')

        doc2 = req.create_entity('File', data=Binary('How I met Babar'))
        fold2 = req.create_entity('Folder', name=u'Celeste bio',
                                  element=doc2, documents=projeid)

    def test_project_and_folder(self):
        req = self.session
        babar = req.execute('Project P WHERE P name "Babar"').get_entity(0,0)

        # start from File (in the Folder sub-container)
        thefile = req.execute('File F WHERE FO element F, FO name like "Babar%"').get_entity(0,0)
        self.assertEqual(['Babar documentation', 'Babar'], parent_titles(thefile))
        thefile = req.execute('File F WHERE FO element F, FO name like "Celeste%"').get_entity(0,0)
        self.assertEqual(['Celeste bio', 'Celeste', 'Babar'], parent_titles(thefile))

        # start from Patch (in Project)
        patch = req.execute('Patch P WHERE EXISTS(P project X)').get_entity(0,0)
        self.assertEqual(['think about it', 'Babar'], parent_titles(patch))

    def test_clone(self):
        req = self.session
        babar = req.execute('Project P WHERE P name "Babar"').get_entity(0,0)
        celeste = req.execute('Project P WHERE P name "Celeste"').get_entity(0,0)
        self.assertEqual([('Folder', u'Babar documentation'),
                          ('Patch', u'some code'),
                          ('Project', u'Celeste'),
                          ('Ticket', u'think about it'),
                          ('Version', u'0.1.0')],
                         sorted([(e.__regid__, e.dc_title())
                                 for e in babar.reverse_project]))
        self.assertEqual([('Folder', u'Celeste bio'),
                          ('Patch', u'bio part one'),
                          ('Ticket', u'write bio'),
                          ('Version', u'0.1.0')],
                         sorted([(e.__regid__, e.dc_title())
                                 for e in celeste.reverse_project]))

        babar_eids = set(x.eid for x in babar.reverse_project)
        celeste_eids = set(x.eid for x in celeste.reverse_project)

        clone = req.create_entity('Project', name=u'Babar clone')
        cloner = clone.cw_adapt_to('Container.clone')
        self.assertEqual(['Folder', 'Patch', 'Project', 'Ticket', 'Version'],
                         sorted(cloner.clonable_etypes()))

        with self.session.deny_all_hooks_but(*clone.compulsory_hooks_categories):
            cloner.clone(original=babar.eid)
            self.commit()

        clone.cw_clear_all_caches()
        self.assertEqual([('Folder', u'Babar documentation'),
                          ('Patch', u'some code'),
                          ('Project', u'Celeste'),
                          ('Ticket', u'think about it'),
                          ('Version', u'0.1.0')],
                         sorted([(e.__regid__, e.dc_title())
                                 for e in clone.reverse_project]))

        self.assertNotEqual(babar_eids, set(x.eid for x in clone.reverse_project))
        cloned_celeste = clone.reverse_subproject_of[0]
        self.assertEqual([('Folder', u'Celeste bio'),
                          ('Patch', u'bio part one'),
                          ('Ticket', u'write bio'),
                          ('Version', u'0.1.0')],
                         sorted([(e.__regid__, e.dc_title())
                                 for e in cloned_celeste.reverse_project]))
        self.assertNotEqual(celeste_eids, set(x.eid for x in cloned_celeste.reverse_project))
