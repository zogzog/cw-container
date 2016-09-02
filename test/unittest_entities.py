from logilab.common.testlib import unittest_main
from cubicweb import ValidationError
from cubicweb.devtools import testlib

from cubes.container.testutils import ContainerTC


class ContainerLessTC(testlib.CubicWebTC):

    def test_free_from_container(self):
        with self.admin_access.repo_cnx() as cnx:
            l = cnx.create_entity('Left')
            self.assertIsNone(l.cw_adapt_to('Container').related_container)
            self.assertIsNone(l.cw_adapt_to('Container').parent)
            cnx.commit()
            self.assertIsNone(l.cw_adapt_to('Container').related_container)
            self.assertIsNone(l.cw_adapt_to('Container').parent)


class ContainerEntitiesTC(ContainerTC):

    def setup_database(self):
        with self.admin_access.repo_cnx() as cnx:
            self.d = cnx.create_entity('Diamond', name=u'Top')
            self.l = cnx.create_entity('Left', top_from_left=self.d)
            self.assertEqual(self.d.eid, self.l.cw_adapt_to('Container').related_container.eid)
            self.r = cnx.create_entity('Right', top_from_right=self.d, to_inner_left=self.l)
            self.b1 = cnx.create_entity('Bottom', top_by_left=self.l)
            self.b2 = cnx.create_entity('Bottom', top_by_right=self.r)
            cnx.commit()

    def test_clone_entry_point(self):
        # the Mess container hasn't got any `is_clone_of` kind of relation
        # we test here that .clone will only work called
        # as .clone(original=original.eid)
        with self.admin_access.repo_cnx() as cnx:
            newd = cnx.create_entity('Mess')
            cloner = newd.cw_adapt_to('Container.clone')
            self.assertRaises(TypeError, cloner.clone)
            self.assertRaises(TypeError, cloner.clone, original=newd)
            cloner.clone(original=newd.eid)
            cnx.commit()

    def test_is_clone_of_relation(self):
        """This triggers a clone through setting the cloning relation"""
        self.assertEqual([u'Bottom -> Left -> Diamond (Top)',
                          u'Bottom -> Right -> Diamond (Top)',
                          u'Diamond (Top)',
                          u'Left -> Diamond (Top)',
                          u'Right -> Diamond (Top)'],
                         sorted([x.dc_title() for x in self.d.reverse_diamond]))
        with self.admin_access.repo_cnx() as cnx:
            newd = cnx.create_entity('Diamond', name=u'TopClone')
            newd.cw_set(is_clone_of=self.d)
            cnx.commit()
            newd = cnx.entity_from_eid(newd.eid)
            self.assertEqual([u'Bottom -> Left -> Diamond (TopClone)',
                              u'Bottom -> Right -> Diamond (TopClone)',
                              u'Diamond (TopClone)',
                              u'Left -> Diamond (TopClone)',
                              u'Right -> Diamond (TopClone)'],
                             sorted([x.dc_title() for x in newd.reverse_diamond]))

    def test_container_relation_hook(self):
        with self.admin_access.repo_cnx() as cnx:
            u = cnx.create_entity('NearTop', reverse_has_near_top=self.d)
            notinside = cnx.create_entity('EtypeNotInContainers',
                                          composite_but_not_in_diamond=self.l)
            cnx.commit()
            notinside = cnx.entity_from_eid(notinside.eid)
            # notinside has a computable parent but no related container
            self.assertNone(notinside.cw_adapt_to('Container'))
            u = cnx.entity_from_eid(u.eid)
            self.assertEqual(self.d.eid, u.cw_adapt_to('Container').parent.eid)
            self.assertEqual(self.d.eid, u.cw_adapt_to('Container').related_container.eid)

    def test_container_rtype_hook(self):
        with self.admin_access.repo_cnx() as cnx:
            self.assertEqual(5, len(cnx.execute('Any X,Y WHERE X diamond Y')))
            l = cnx.entity_from_eid(self.l.eid)
            self.assertEqual(self.d.eid, l.cw_adapt_to('Container').related_container.eid)
            self.assertEqual('Diamond', l.container_etype[0].name)
            self.assertEqual(l.eid, self.b1.cw_adapt_to('Container').parent.eid)
            self.assertEqual(self.r.eid, self.b2.cw_adapt_to('Container').parent.eid)

            m = cnx.create_entity('Mess')
            b3 = cnx.create_entity('Bottom', to_mess=m)
            # relocating through another rtype / to another container is forbiden
            with self.assertRaises(ValidationError) as wraperr:
                b3.cw_set(top_by_left=l)
            self.assertEqual({'top_by_left': u'Bottom is already in a container through top_by_left'},
                             wraperr.exception.args[1])
            cnx.rollback()

            m = cnx.create_entity('Mess')
            self.assertRaises(ValidationError, cnx.create_entity,
                              'Bottom', to_mess=m, top_by_left=l)
            cnx.rollback()

            i = cnx.create_entity('IAmAnAttributeCarryingRelation',
                                  foo=42, to_left=l, to_right=self.r)
            cnx.commit()
            self.assertEqual(l.eid, i.to_left[0].eid)
            self.assertEqual(self.r.eid, i.to_right[0].eid)

    def test_relocate_to_other_parent(self):
        with self.admin_access.repo_cnx() as cnx:
            b1 = cnx.entity_from_eid(self.b1.eid)
            self.assertEqual(self.l.eid, b1.cw_adapt_to('Container').parent.eid)
            l2 = cnx.create_entity('Left', top_from_left=self.d)
            cnx.commit()
            # relocate within same container/same rtype
            b1 = cnx.entity_from_eid(self.b1.eid)
            self.assertEqual(self.l.eid, b1.cw_adapt_to('Container').parent.eid)
            b1.cw_set(top_by_left=l2.eid)
            self.assertEqual(l2.eid, b1.cw_adapt_to('Container').parent.eid)
            cnx.commit()
            # relocate within same container/different rtype
            b1 = cnx.entity_from_eid(self.b1.eid)
            self.assertEqual(l2.eid, b1.cw_adapt_to('Container').parent.eid)
            with self.assertRaises(ValidationError) as wraperr:
                b1.cw_set(top_by_right=self.r.eid)
            self.assertEqual({'top_by_right': u'Bottom is already in a container through top_by_right'},
                             wraperr.exception.args[1])
            # relocate to different container/same rtype
            b1 = cnx.entity_from_eid(self.b1.eid)
            d2 = cnx.create_entity('Diamond')
            l3 = cnx.create_entity('Left', top_from_left=d2)
            with self.assertRaises(ValidationError) as wraperr:
                b1.cw_set(top_by_left=l3)
            self.assertEqual({'top_by_left': u'Bottom is already in a container through top_by_left'},
                             wraperr.exception.args[1])

if __name__ == '__main__':
    unittest_main()
