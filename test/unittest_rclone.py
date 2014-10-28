import time
from logilab.common.testlib import unittest_main

from cubicweb import Binary, ValidationError

from cubes.container import utils
from cubes.container.config import Container
from cubes.container.testutils import (userlogin, new_version, new_ticket,
                                       new_patch, new_card)
from cubes.container.testutils import rdefrepr, ContainerTC


class TwoContainersTC(ContainerTC):
    appid = 'data-tracker'

    def test_needs_container_parent(self):
        needs_cp = set(eschema.type
                       for eschema in self.schema.entities()
                       if utils.needs_container_parent(eschema))
        self.assertEqual(['CWAttribute', 'CWRelation', 'CWSourceSchemaConfig',
                          'Card', 'Folder', 'RQLExpression'],
                         sorted(needs_cp))

    # Project
    def test_project_rdefs(self):
        schema = self.vreg.schema
        project = Container.by_etype('Project')

        self.assertEqual(set([('requirement', 'Ticket', 'Card'),
                              ('documents', 'Folder', 'Project'),
                              ('version_of', 'Version', 'Project'),
                              ('concerns', 'Ticket', 'Project'),
                              ('implements', 'Patch', 'Ticket'),
                              ('subproject_of', 'Project', 'Project')]),
                         set([rdefrepr(rdef) for rdef in project.rdefs]))

        self.assertEqual(set([('implements', 'Patch', 'Ticket'),
                              ('done_in_version', 'Ticket', 'Version'),
                              ('concerns', 'Ticket', 'Project'),
                              ('version_of', 'Version', 'Project'),
                              ('subproject_of', 'Project', 'Project'),
                              ('documents', 'Folder', 'Project'),
                              ('requirement', 'Ticket', 'Card')]),
                         set([rdefrepr(rdef) for rdef in project.inner_rdefs]))
        self.assertEqual(set([('canread', 'CWUser', 'Project'),
                              ('canwrite', 'CWUser', 'Project')]),
                         set([rdefrepr(rdef) for rdef in project.border_rdefs]))

        self.assertEqual(frozenset(['Card', 'Patch', 'Ticket', 'Version', 'Folder','Project']),
                         project.etypes)


    def test_order(self):
        project = Container.by_etype('Project')
        self.assertEqual(['Project', 'Folder', 'Ticket', 'Card', 'Version', 'Patch'],
                         project.ordered_etypes)

        folder = Container.by_etype('Folder')
        self.assertEqual(['Folder', 'Card', 'XFile'],
                         folder.ordered_etypes)

    def test_project_hooks(self):
        schema = self.vreg.schema
        project = Container.by_etype('Project')
        self.assertEqual({'documents': set([('Folder', 'Project')]),
                          'requirement': set([('Ticket', 'Card')])},
                         project._container_parent_rdefs)

    # Folder
    def test_folder_rdefs(self):
        schema = self.vreg.schema
        folder = Container.by_etype('Folder')

        self.assertEqual(set([('element', 'Folder', 'XFile'),
                              ('parent', 'Folder', 'Folder'),
                              ('element', 'Folder', 'Card')]),
                         set([rdefrepr(rdef) for rdef in folder.rdefs]))
        self.assertEqual(set([('element', 'Folder', 'XFile'),
                              ('parent', 'Folder', 'Folder'),
                              ('element', 'Folder', 'Card')]),
                         set([rdefrepr(rdef) for rdef in folder.inner_rdefs]))
        self.assertEqual(set([('documents', 'Folder', 'Project'),
                              ('content', 'Patch', 'XFile'),
                              ('requirement', 'Ticket', 'Card')]),
                         set([rdefrepr(rdef) for rdef in folder.border_rdefs]))

        self.assertEqual((frozenset(['parent', 'element']),
                          frozenset(['Card', 'Folder', 'XFile'])),
                         utils.container_static_structure(schema,
                                                          folder.cetype,
                                                          folder.crtype,
                                                          skiprtypes=folder.skiprtypes,
                                                          skipetypes=folder.skipetypes))

    def test_folder_etypes_rtypes(self):
        schema = self.vreg.schema
        folder = Container.by_etype('Folder')
        self.assertEqual((frozenset(['parent', 'element']),
                          frozenset(['Card', 'Folder', 'XFile'])),
                         utils.container_rtypes_etypes(schema,
                                                       folder.cetype,
                                                       folder.crtype,
                                                       skiprtypes=folder.skiprtypes,
                                                       skipetypes=folder.skipetypes))

    def test_folder_hooks(self):
        schema = self.vreg.schema
        folder = Container.by_etype('Folder')
        self.assertEqual(set(['parent', 'element']),
                         utils.set_container_parent_rtypes_hook(schema,
                                                                folder.cetype,
                                                                folder.crtype,
                                                                skiprtypes=folder.skiprtypes,
                                                                skipetypes=folder.skipetypes,
                                                                subcontainers=folder.subcontainers))
        self.assertEqual({'parent': set([('Folder', 'Folder')]),
                          'element': set([('Folder', 'Card')])},
                         utils.container_parent_rdefs(schema,
                                                      folder.cetype,
                                                      folder.crtype,
                                                      skiprtypes=folder.skiprtypes,
                                                      skipetypes=folder.skipetypes,
                                                      subcontainers=folder.subcontainers))
        self.assertEqual(set(('parent', 'element')),
                         utils.set_container_relation_rtypes_hook(schema,
                                                                  folder.cetype,
                                                                  folder.crtype,
                                                                  skiprtypes=folder.skiprtypes,
                                                                  skipetypes=folder.skipetypes,
                                                                  subcontainers=folder.subcontainers))

def parent_titles(parent):
    parents = []
    while True:
        parent = parent.cw_adapt_to('Container').parent
        if parent is None:
            break
        parents.append(parent.dc_title())
    return parents

class CloneTC(ContainerTC):
    appid = 'data-tracker'
    userlogin = userlogin

    def setup_database(self):
        session = self.session
        proj = session.create_entity('Project', name=u'Babar')
        projeid = session.execute('Project P').get_entity(0, 0)
        ver = new_version(session, projeid)

        tick = new_ticket(session, projeid, ver)
        card = new_card(session)
        tick.cw_set(requirement=card)

        afile = session.create_entity('XFile', data=Binary('foo'))
        patch = new_patch(session, tick, afile)

        doc1 = session.create_entity('XFile', data=Binary('How I became King'))
        fold1 = session.create_entity('Folder', name=u'Babar documentation',
                                      element=doc1, documents=projeid)
        card = new_card(session, u'Some doc bit')
        fold1.cw_set(element=card)

        # a subproject
        proj = session.create_entity('Project', name=u'Celeste',
                                     subproject_of=proj)
        projeid = proj.eid
        ver = new_version(session, projeid)
        tick = new_ticket(session, projeid, ver, name=u'write bio', descr=u'do it')
        card = new_card(session, u'Write me')
        tick.cw_set(requirement=card)

        afile = session.create_entity('XFile', data=Binary('foo'))
        patch = new_patch(session, tick, afile, name=u'bio part one')

        doc2 = session.create_entity('XFile', data=Binary('How I met Babar'))
        fold2 = session.create_entity('Folder', name=u'Celeste bio',
                                  element=doc2, documents=projeid)
        card = new_card(session, u'A general doc item')
        fold2.cw_set(element=card)

    def test_project_and_folder(self):
        session = self.session
        babar = session.execute('Project P WHERE P name "Babar"').get_entity(0,0)

        # start from XFile (in the Folder sub-container)
        thefile = session.execute('XFile F WHERE FO element F, FO name like "Babar%"').get_entity(0,0)
        self.assertEqual(['Babar documentation', 'Babar'], parent_titles(thefile))
        thefile = session.execute('XFile F WHERE FO element F, FO name like "Celeste%"').get_entity(0,0)
        self.assertEqual(['Celeste bio', 'Celeste', 'Babar'], parent_titles(thefile))

        # start from Card (in Folder)
        card1, card2 = list(session.execute('Card C ORDERBY C WHERE C folder_root F').entities())
        self.assertEqual([u'Babar documentation', u'Babar'], parent_titles(card1))
        self.assertEqual([u'Celeste bio', u'Celeste', u'Babar'], parent_titles(card2))

        # start from Card (in Folder)
        card1, card2 = list(session.execute('Card C ORDERBY C WHERE C project P').entities())
        self.assertEqual([u'think about it', u'Babar'], parent_titles(card1))
        self.assertEqual([u'write bio', u'Celeste', u'Babar'], parent_titles(card2))

        # start from Patch (in Project)
        patch = session.execute('Patch P WHERE P project X, X name "Babar"').get_entity(0,0)
        self.assertEqual(['think about it', 'Babar'], parent_titles(patch))

        patch = session.execute('Patch P WHERE P project X, X name "Celeste"').get_entity(0,0)
        self.assertEqual(['write bio', 'Celeste', 'Babar'], parent_titles(patch))

        foldr = session.execute('Folder F WHERE F name "Babar documentation"').get_entity(0,0)

        self.assertEqual([babar], foldr.project)
        self.assertEqual([foldr], foldr.folder_root)

    def test_clone(self):
        session = self.session
        self.assertEqual(6, session.execute('Any COUNT(X) WHERE X container_parent Y').rows[0][0])
        self.assertEqual(0, session.execute('Any COUNT(X) WHERE NOT X container_parent Y').rows[0][0])
        babar = session.execute('Project P WHERE P name "Babar"').get_entity(0,0)
        celeste = session.execute('Project P WHERE P name "Celeste"').get_entity(0,0)
        babar_contents = [('Card', u"Let's start a spec ..."),
                          ('Folder', u'Babar documentation'),
                          ('Patch', u'some code'),
                          ('Project', u'Babar'),
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
        babar_doc = session.execute('Folder F WHERE F name "Babar documentation"').get_entity(0, 0)
        celeste_doc = session.execute('Folder F WHERE F name "Celeste bio"').get_entity(0, 0)
        babar_doc_contents = [('XFile', 'How I became King'),
                              ('Card', u'Some doc bit')]
        celeste_doc_contents = [('XFile', 'How I met Babar'),
                                ('Card', u'A general doc item')]
        self.assertEqual(frozenset(babar_doc_contents),
                         frozenset((e.cw_etype, e.dc_title() or e.data.getvalue())
                                   for e in babar_doc.element))
        self.assertEqual(frozenset(celeste_doc_contents),
                         frozenset((e.cw_etype, e.dc_title() or e.data.getvalue())
                                   for e in celeste_doc.element))

        babar_eids = set(x.eid for x in babar.reverse_project)
        celeste_eids = set(x.eid for x in celeste.reverse_project)

        self.assertEqual(1, session.execute('Any X WHERE X has_text "Celeste"').rowcount)

        clone = session.create_entity('Project', name=u'Babar clone')
        self.commit()
        cloner = clone.cw_adapt_to('Container.clone')
        self.assertEqual(['Card', 'Folder', 'Patch', 'Project', 'Ticket', 'Version'],
                         sorted(cloner.clonable_etypes()))

        with self.session.deny_all_hooks_but(*cloner.config.compulsory_hooks_categories):
            cloner.clone(original=babar.eid)
            self.commit()

        # run the task for deferred hooks
        session = self.session
        task = session.execute('CWWorkerTask T WHERE T operation "run-deferred-hooks"').get_entity(0,0)
        hooksrunner = self.vreg['worker.performer'].select('run-deferred-hooks', session)
        hooksrunner.perform_task(session, task)
        session.commit()

        session = self.session
        self.assertEqual(2, session.execute('Any X WHERE X has_text "Celeste"').rowcount)

        clone.cw_clear_all_caches()
        babar_clone_contents = [('Card', u"Let's start a spec ..."),
                                ('Folder', u'Babar documentation'),
                                ('Patch', u'some code'),
                                ('Project', u'Babar clone'),
                                ('Project', u'Celeste'),
                                ('Ticket', u'think about it'),
                                ('Version', u'0.1.0')]
        self.assertEqual(babar_clone_contents,
                         sorted([(e.__regid__, e.dc_title())
                                 for e in clone.reverse_project]))

        self.assertNotEqual(babar_eids, set(x.eid for x in clone.reverse_project))
        cloned_celeste = clone.reverse_subproject_of[0]
        self.assertEqual(celeste_contents,
                         sorted([(e.__regid__, e.dc_title())
                                 for e in cloned_celeste.reverse_project]))
        self.assertNotEqual(celeste_eids, set(x.eid for x in cloned_celeste.reverse_project))

        # check container_parent, container_etype, created_by, owned_by, is_instance_of
        session = self.session

        patch = session.execute('Patch P WHERE P project X, X name "Babar"').get_entity(0,0)
        self.assertEqual('XFile', patch.content[0].__regid__)
        cloned_patch = session.execute('Patch P WHERE P project X, X name "Babar clone"').get_entity(0,0)
        self.assertEqual('XFile', cloned_patch.content[0].__regid__)

        self.assertTrue(cloned_patch.cw_source) # this was properly relinked (external relation)
        cloned_version = session.execute('Version V WHERE V version_of P, '
                                         'P name "Babar clone"').get_entity(0,0)
        cloned_ticket = session.execute('Ticket T WHERE T concerns P, '
                                        'P name "Babar clone"').get_entity(0,0)
        self.assertEqual([cloned_version], cloned_ticket.done_in_version)

        folder = session.execute('Folder F WHERE F project P, P name "Babar"').get_entity(0,0)
        cloned_folder = session.execute('Folder F WHERE F project P, P name "Babar clone"').get_entity(0,0)

        # check internal relinking wrt crtype
        self.assertEqual([folder], folder.folder_root)
        self.assertEqual([cloned_folder], cloned_folder.folder_root)

        # parent and various metadata
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
        # container_parent must be correctly handled, let's watch potential regressions
        self.assertEqual(12, session.execute('Any COUNT(X) WHERE X container_parent Y').rows[0][0])
        self.assertEqual(0, session.execute('Any COUNT(X) WHERE NOT X container_parent Y').rows[0][0])

    def test_clone_other_user(self):
        """ Demonstrate proper handling of metadata by the cloning process """
        user_eid = self.create_user(self.request(), u'bob').eid
        self.request().execute('SET U canread P '
                               'WHERE P is Project, P name "Babar",'
                               '      U login "bob"')
        self.commit()
        with self.login('bob'):
            req = self.session
            babar = req.execute('Project P WHERE P name "Babar"').get_entity(0,0)
            babar.creation_date # set in entity cache
            babar.modification_date # idem
            clone = req.create_entity('Project', name=u'Babar clone')
            clone_eid = clone.eid
            cloner = clone.cw_adapt_to('Container.clone')
            with self.session.deny_all_hooks_but(*cloner.config.compulsory_hooks_categories):
                cloner.clone(original=babar.eid)
                self.commit()
        time.sleep(.1)
        with self.login('bob'):
            req = self.request()
            project = req.execute('Project P WHERE P name "Babar clone"').get_entity(0,0)
            folder = req.execute('Folder F WHERE F project P, P name "Babar clone"').get_entity(0,0)
            user = req.entity_from_eid(user_eid)
            self.assertEqual([user], project.owned_by)
            self.assertEqual([user], folder.owned_by)
            self.assertEqual([user], folder.created_by)
            self.assertTrue(project.creation_date > babar.creation_date)
            self.assertTrue(project.modification_date > babar.modification_date)
