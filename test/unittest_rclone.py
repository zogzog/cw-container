import time
from cubicweb import Binary

from cubes.container import utils
from cubes.container.config import Container
from cubes.container.testutils import (new_version, new_ticket,
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
        project = Container.by_etype('Project')
        self.assertEqual({'documents': set([('Folder', 'Project')]),
                          'requirement': set([('Ticket', 'Card')])},
                         project._container_parent_rdefs)

    # Folder
    def test_folder_rdefs(self):
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

    def setup_database(self):
        with self.admin_access.repo_cnx() as cnx:
            proj = cnx.create_entity('Project', name=u'Babar')
            projeid = proj.eid
            ver = new_version(cnx, projeid)

            tick = new_ticket(cnx, projeid, ver)
            card = new_card(cnx)
            tick.cw_set(requirement=card)

            afile = cnx.create_entity('XFile', data=Binary('foo'))
            patch = new_patch(cnx, tick, afile)

            doc1 = cnx.create_entity('XFile', data=Binary('How I became King'))
            fold1 = cnx.create_entity('Folder', name=u'Babar documentation',
                                      element=doc1, documents=projeid)
            card = new_card(cnx, u'Some doc bit')
            fold1.cw_set(element=card)

            # a subproject
            proj = cnx.create_entity('Project', name=u'Celeste',
                                     subproject_of=proj)
            projeid = proj.eid
            ver = new_version(cnx, projeid)
            tick = new_ticket(cnx, projeid, ver, name=u'write bio', descr=u'do it')
            card = new_card(cnx, u'Write me')
            tick.cw_set(requirement=card)

            afile = cnx.create_entity('XFile', data=Binary('foo'))
            patch = new_patch(cnx, tick, afile, name=u'bio part one')

            doc2 = cnx.create_entity('XFile', data=Binary('How I met Babar'))
            fold2 = cnx.create_entity('Folder', name=u'Celeste bio',
                                      element=doc2, documents=projeid)
            card = new_card(cnx, u'A general doc item')
            fold2.cw_set(element=card)
            cnx.commit()

    def test_project_and_folder(self):
        with self.admin_access.repo_cnx() as cnx:
            babar = cnx.find('Project', name=u'Babar').one()

            # start from XFile (in the Folder sub-container)
            thefile = cnx.execute('XFile F WHERE FO element F, FO name like "Babar%"').one()
            self.assertEqual(['Babar documentation', 'Babar'], parent_titles(thefile))
            thefile = cnx.execute('XFile F WHERE FO element F, FO name like "Celeste%"').one()
            self.assertEqual(['Celeste bio', 'Celeste', 'Babar'], parent_titles(thefile))

            # start from Card (in Folder)
            card1, card2 = list(cnx.execute('Card C ORDERBY C WHERE C folder_root F').entities())
            self.assertEqual([u'Babar documentation', u'Babar'], parent_titles(card1))
            self.assertEqual([u'Celeste bio', u'Celeste', u'Babar'], parent_titles(card2))

            # start from Card (in Folder)
            card1, card2 = list(cnx.execute('Card C ORDERBY C WHERE C project P').entities())
            self.assertEqual([u'think about it', u'Babar'], parent_titles(card1))
            self.assertEqual([u'write bio', u'Celeste', u'Babar'], parent_titles(card2))

            # start from Patch (in Project)
            patch = cnx.execute('Patch P WHERE P project X, X name "Babar"').one()
            self.assertEqual(['think about it', 'Babar'], parent_titles(patch))

            patch = cnx.execute('Patch P WHERE P project X, X name "Celeste"').one()
            self.assertEqual(['write bio', 'Celeste', 'Babar'], parent_titles(patch))

            foldr = cnx.find('Folder', name=u'Babar documentation').one()

            self.assertEqual([babar], foldr.project)
            self.assertEqual([foldr], foldr.folder_root)

    def test_clone(self):
        with self.admin_access.repo_cnx() as cnx:
            self.assertEqual(6, cnx.execute('Any COUNT(X) WHERE X container_parent Y').rows[0][0])
            self.assertEqual(0, cnx.execute('Any COUNT(X) WHERE NOT X container_parent Y').rows[0][0])
            babar = cnx.find('Project', name=u'Babar').one()
            celeste = cnx.find('Project', name=u'Celeste').one()
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
            babar_doc = cnx.find('Folder', name=u'Babar documentation').one()
            celeste_doc = cnx.find('Folder', name=u'Celeste bio').one()
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

            self.assertEqual(1, cnx.execute('Any X WHERE X has_text "Celeste"').rowcount)

            clone = cnx.create_entity('Project', name=u'Babar clone')
            cnx.commit()
            cloner = clone.cw_adapt_to('Container.clone')
            self.assertEqual(['Card', 'Folder', 'Patch', 'Project', 'Ticket', 'Version'],
                             sorted(cloner.clonable_etypes()))

            with cnx.deny_all_hooks_but(*cloner.config.compulsory_hooks_categories):
                cloner.clone(original=babar.eid)
                cnx.commit()

            # run the task for deferred hooks
            task = cnx.find('CWWorkerTask', operation=u'run-deferred-hooks').one()
            hooksrunner = self.vreg['worker.performer'].select('run-deferred-hooks')
            hooksrunner.perform_task(cnx, task)
            cnx.commit()

            self.assertEqual(2, cnx.execute('Any X WHERE X has_text "Celeste"').rowcount)

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
            patch = cnx.execute('Patch P WHERE P project X, X name "Babar"').one()
            self.assertEqual('XFile', patch.content[0].__regid__)
            cloned_patch = cnx.execute('Patch P WHERE P project X, X name "Babar clone"').one()
            self.assertEqual('XFile', cloned_patch.content[0].__regid__)

            self.assertTrue(cloned_patch.cw_source) # this was properly relinked (external relation)
            cloned_version = cnx.execute('Version V WHERE V version_of P, '
                                         'P name "Babar clone"').one()
            cloned_ticket = cnx.execute('Ticket T WHERE T concerns P, '
                                        'P name "Babar clone"').one()
            self.assertEqual([cloned_version], cloned_ticket.done_in_version)

            folder = cnx.execute('Folder F WHERE F project P, P name "Babar"').one()
            cloned_folder = cnx.execute('Folder F WHERE F project P, P name "Babar clone"').one()

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
            self.assertEqual(str(cloned_folder.eid), cloned_folder.cwuri)
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
            self.assertEqual(12, cnx.execute('Any COUNT(X) WHERE X container_parent Y').rows[0][0])
            self.assertEqual(0, cnx.execute('Any COUNT(X) WHERE NOT X container_parent Y').rows[0][0])

    def test_clone_other_user(self):
        """ Demonstrate proper handling of metadata by the cloning process """
        with self.admin_access.repo_cnx() as cnx:
            user_eid = self.create_user(cnx, u'bob').eid
            cnx.execute('SET U canread P '
                        'WHERE P is Project, P name "Babar",'
                        '      U login "bob"')
            cnx.commit()
        with self.new_access('bob').repo_cnx() as cnx:
            babar = cnx.find('Project', name=u'Babar').one()
            babar.creation_date # set in entity cache
            babar.modification_date # idem
            clone = cnx.create_entity('Project', name=u'Babar clone')
            clone_eid = clone.eid
            cloner = clone.cw_adapt_to('Container.clone')
            with cnx.deny_all_hooks_but(*cloner.config.compulsory_hooks_categories):
                cloner.clone(original=babar.eid)
                cnx.commit()
        time.sleep(.1)
        with self.new_access('bob').repo_cnx() as cnx:
            project = cnx.find('Project', name=u'Babar clone').one()
            folder = cnx.execute('Folder F WHERE F project P, P name "Babar clone"').get_entity(0,0)
            user = cnx.entity_from_eid(user_eid)
            self.assertEqual([user], project.owned_by)
            self.assertEqual([user], folder.owned_by)
            self.assertEqual([user], folder.created_by)
            self.assertTrue(project.creation_date > babar.creation_date)
            self.assertTrue(project.modification_date > babar.modification_date)
