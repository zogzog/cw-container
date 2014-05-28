from logilab.common.testlib import unittest_main

from cubicweb import Binary, ValidationError
from cubicweb.devtools.testlib import CubicWebTC

from cubes.container import _needs_container_parent
from cubes.container.testutils import (userlogin, new_version, new_ticket,
                                       new_patch, new_card, ContainerMixinTC)


class TwoContainersTC(ContainerMixinTC, CubicWebTC):
    appid = 'data-forge2'

    def test_needs_container_parent(self):
        needs_cp = set(eschema.type
                       for eschema in self.schema.entities()
                       if _needs_container_parent(eschema))
        self.assertEqual(['CWAttribute', 'CWRelation', 'CWSourceSchemaConfig',
                          'Card', 'Folder', 'RQLExpression'],
                         sorted(needs_cp))

    # Project
    def test_project_structure(self):
        from config import PROJECT_CONTAINER
        self.assertEqual((frozenset(['documents', 'implements', 'concerns', 'version_of',
                                     'subproject_of', 'requirement']),
                          frozenset(['Card', 'Patch', 'Ticket', 'Version', 'Folder','Project'])),
                         PROJECT_CONTAINER.structure(self.vreg.schema))


    def test_project_inner(self):
        from config import PROJECT_CONTAINER
        # NOTE: this contains 'parent' and 'element', which is WRONG
        # However, short of fully specifying the subcontainer (not just the top entity type)
        # we cannot do much against that. We really need some support viz Yams
        # (e.g. http://www.logilab.org/ticket/100723)
        self.assertEqual(set(['parent', 'done_in_version', 'element']),
                         set(PROJECT_CONTAINER.inner_relations(self.vreg.schema)))


    def test_project_hooks(self):
        from config import PROJECT_CONTAINER
        self.assertEqual({'documents': set([('Folder', 'Project')]),
                          'requirement': set([('Ticket', 'Card')])},
                         PROJECT_CONTAINER._container_parent_rdefs(self.vreg.schema))

    # Folder
    def test_folder_static_structure(self):
        from config import FOLDER_CONTAINER
        self.assertEqual((frozenset(['parent', 'element']),
                          frozenset(['Card', 'Folder', 'File'])),
                         FOLDER_CONTAINER.structure(self.vreg.schema))

    def test_folder_inner(self):
        from config import FOLDER_CONTAINER
        self.assertEqual(set([]),
                         set(FOLDER_CONTAINER.inner_relations(self.vreg.schema)))

    def test_folder_hooks(self):
        from config import FOLDER_CONTAINER
        self.assertEqual({'parent': set([('Folder', 'Folder')]),
                          'element': set([('Folder', 'Card')])},
                         FOLDER_CONTAINER._container_parent_rdefs(self.vreg.schema))

def parent_titles(parent):
    parents = []
    while True:
        parent = parent.cw_adapt_to('Container').parent
        if parent is None:
            break
        parents.append(parent.dc_title())
    return parents


class CloneTC(ContainerMixinTC, CubicWebTC):
    userlogin = userlogin
    appid = 'data-forge2'

    def setup_database(self):
        req = self.request()
        proj = req.create_entity('Project', name=u'Babar')
        projeid = req.execute('Project P').get_entity(0, 0)
        ver = new_version(req, projeid)

        tick = new_ticket(req, projeid, ver)
        card = new_card(req)
        tick.cw_set(requirement=card)

        afile = req.create_entity('File', data=Binary('foo'))
        patch = new_patch(req, tick, afile)

        doc1 = req.create_entity('File', data=Binary('How I became King'))
        fold1 = req.create_entity('Folder', name=u'Babar documentation',
                                  element=doc1, documents=projeid)
        card = new_card(req, u'Some doc bit')
        fold1.cw_set(element=card)

        # a subproject
        proj = req.create_entity('Project', name=u'Celeste',
                                 subproject_of=proj)
        projeid = proj.eid
        ver = new_version(req, projeid)
        tick = new_ticket(req, projeid, ver, name=u'write bio', descr=u'do it')
        card = new_card(req, u'Write me')
        tick.cw_set(requirement=card)

        afile = req.create_entity('File', data=Binary('foo'))
        patch = new_patch(req, tick, afile, name=u'bio part one')

        doc2 = req.create_entity('File', data=Binary('How I met Babar'))
        fold2 = req.create_entity('Folder', name=u'Celeste bio',
                                  element=doc2, documents=projeid)
        card = new_card(req, u'A general doc item')
        fold2.cw_set(element=card)

    def test_project_and_folder(self):
        req = self.session
        babar = req.execute('Project P WHERE P name "Babar"').get_entity(0,0)

        # start from File (in the Folder sub-container)
        thefile = req.execute('File F WHERE FO element F, FO name like "Babar%"').get_entity(0,0)
        self.assertEqual(['Babar documentation', 'Babar'], parent_titles(thefile))
        thefile = req.execute('File F WHERE FO element F, FO name like "Celeste%"').get_entity(0,0)
        self.assertEqual(['Celeste bio', 'Celeste', 'Babar'], parent_titles(thefile))

        # start from Card (in Folder)
        card1, card2 = list(req.execute('Card C ORDERBY C WHERE C folder_root F').entities())
        self.assertEqual([u'Babar documentation', u'Babar'], parent_titles(card1))
        self.assertEqual([u'Celeste bio', u'Celeste', u'Babar'], parent_titles(card2))

        # start from Card (in Folder)
        card1, card2 = list(req.execute('Card C ORDERBY C WHERE C project P').entities())
        self.assertEqual([u'think about it', u'Babar'], parent_titles(card1))
        self.assertEqual([u'write bio', u'Celeste', u'Babar'], parent_titles(card2))

        # start from Patch (in Project)
        patch = req.execute('Patch P WHERE P project X, X name "Babar"').get_entity(0,0)
        self.assertEqual(['think about it', 'Babar'], parent_titles(patch))

        patch = req.execute('Patch P WHERE P project X, X name "Celeste"').get_entity(0,0)
        self.assertEqual(['write bio', 'Celeste', 'Babar'], parent_titles(patch))

    def test_clone(self):
        req = self.session
        babar = req.execute('Project P WHERE P name "Babar"').get_entity(0,0)
        celeste = req.execute('Project P WHERE P name "Celeste"').get_entity(0,0)
        babar_contents = [('Card', u"Let's start a spec ..."),
                          ('Folder', u'Babar documentation'),
                          ('Patch', u'some code'),
                          ('Project', u'Celeste'),
                          ('Ticket', u'think about it'),
                          ('Version', u'0.1.0')]
        self.assertEqual(babar_contents,
                         sorted([(e.__regid__, e.dc_title())
                                 for e in babar.reverse_project]))
        celeste_contents = [('Card', u'Write me'),
                            ('Folder', u'Celeste bio'),
                            ('Patch', u'bio part one'),
                            ('Ticket', u'write bio'),
                            ('Version', u'0.1.0')]
        self.assertEqual(celeste_contents,
                         sorted([(e.__regid__, e.dc_title())
                                 for e in celeste.reverse_project]))
        # The folder containers contain what they are supposed to:
        babar_doc = req.execute('Folder F WHERE F name "Babar documentation"').get_entity(0, 0)
        celeste_doc = req.execute('Folder F WHERE F name "Celeste bio"').get_entity(0, 0)
        babar_doc_contents = [('File', 'How I became King'),
                              ('Card', u'Some doc bit')]
        celeste_doc_contents = [('File', 'How I met Babar'),
                                ('Card', u'A general doc item')]
        self.assertEqual(frozenset(babar_doc_contents),
                         frozenset((e.cw_etype, e.dc_title() or e.data.getvalue())
                                   for e in babar_doc.element))
        self.assertEqual(frozenset(celeste_doc_contents),
                         frozenset((e.cw_etype, e.dc_title() or e.data.getvalue())
                                   for e in celeste_doc.element))

        babar_eids = set(x.eid for x in babar.reverse_project)
        celeste_eids = set(x.eid for x in celeste.reverse_project)

        clone = req.create_entity('Project', name=u'Babar clone')
        cloner = clone.cw_adapt_to('Container.clone')
        self.assertEqual(['Card', 'Folder', 'Patch', 'Project', 'Ticket', 'Version'],
                         sorted(cloner.clonable_etypes()))

        with self.session.deny_all_hooks_but(*cloner.compulsory_hooks_categories):
            cloner.clone(original=babar.eid)
            self.commit()

        clone.cw_clear_all_caches()
        self.assertEqual(babar_contents,
                         sorted([(e.__regid__, e.dc_title())
                                 for e in clone.reverse_project]))

        self.assertNotEqual(babar_eids, set(x.eid for x in clone.reverse_project))
        cloned_celeste = clone.reverse_subproject_of[0]
        self.assertEqual(celeste_contents,
                         sorted([(e.__regid__, e.dc_title())
                                 for e in cloned_celeste.reverse_project]))
        self.assertNotEqual(celeste_eids, set(x.eid for x in cloned_celeste.reverse_project))

        # check container_parent, container_etype, created_by, owned_by, is_instance_of
        req = self.request()

        patch = req.execute('Patch P WHERE P project X, X name "Babar"').get_entity(0,0)
        self.assertEqual('File', patch.content[0].__regid__)
        cloned_patch = req.execute('Patch P WHERE P project X, X name "Babar clone"').get_entity(0,0)
        self.assertEqual('File', cloned_patch.content[0].__regid__)


        folder = req.execute('Folder F WHERE F project P, P name "Babar"').get_entity(0,0)
        cloned_folder = req.execute('Folder F WHERE F project P, P name "Babar clone"').get_entity(0,0)
        self.assertEqual(folder.cw_adapt_to('Container').parent.__regid__,
                         cloned_folder.cw_adapt_to('Container').parent.__regid__)
        self.assertEqual(folder.container_etype, cloned_folder.container_etype)
        self.assertEqual(folder.created_by, cloned_folder.created_by)
        self.assertEqual(folder.owned_by, cloned_folder.owned_by)
        self.assertEqual(folder.is_instance_of, cloned_folder.is_instance_of)

        self.assertIn(str(folder.eid), folder.cwuri)
        self.assertEqual('', cloned_folder.cwuri)
        # The entities linked via subject composite relations to the container
        # are linked to the cloned container as well:
        self.assertEqual(frozenset(doc.dc_title() or doc.data.getvalue()
                                   for doc in folder.element),
                         frozenset(doc.dc_title() or doc.data.getvalue()
                                   for doc in cloned_folder.element))
        # The entities linked via subject composite relations to the container
        # are actually copied as well:
        self.assertNotEqual(frozenset(doc.eid for doc in folder.element),
                            frozenset(doc.eid for doc in cloned_folder.element))


if __name__ == '__main__':
    unittest_main()

