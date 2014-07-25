from logilab.common.testlib import unittest_main
from cubicweb import ValidationError
from cubicweb.devtools.testlib import CubicWebTC

from cubes.container.testutils import ContainerTC

class ContainerLessTC(CubicWebTC):

    def test_free_from_container(self):
        l = self.session.create_entity('Left')
        self.assertIsNone(l.cw_adapt_to('Container').related_container)
        self.assertIsNone(l.cw_adapt_to('Container').parent)
        self.commit()
        self.assertIsNone(l.cw_adapt_to('Container').related_container)
        self.assertIsNone(l.cw_adapt_to('Container').parent)

class ContainerEntitiesTC(ContainerTC):

    def setup_database(self):
        session = self.session
        self.d = session.create_entity('Diamond', name=u'Top')
        self.l = session.create_entity('Left', top_from_left=self.d)
        self.assertEqual(self.d.eid, self.l.cw_adapt_to('Container').related_container.eid)
        self.r = session.create_entity('Right', top_from_right=self.d, to_inner_left=self.l)
        self.b1 = session.create_entity('Bottom', top_by_left=self.l)
        self.b2 = session.create_entity('Bottom', top_by_right=self.r)

    def test_clone_entry_point(self):
        # the Mess container hasn't got any `is_clone_of` kind of relation
        # we test here that .clone will only work called
        # as .clone(original=original.eid)
        session = self.session
        newd = session.create_entity('Mess')
        cloner = newd.cw_adapt_to('Container.clone')
        self.assertRaises(TypeError, cloner.clone)
        self.assertRaises(TypeError, cloner.clone, original=newd)
        cloner.clone(original=newd.eid)
        self.commit()

    def test_is_clone_of_relation(self):
        """This triggers a clone through setting the cloning relation"""
        self.assertEqual([u'Bottom -> Left -> Diamond (Top)',
                          u'Bottom -> Right -> Diamond (Top)',
                          u'Diamond (Top)',
                          u'Left -> Diamond (Top)',
                          u'Right -> Diamond (Top)'],
                         sorted([x.dc_title() for x in self.d.reverse_diamond]))
        newd = self.session.create_entity('Diamond', name=u'TopClone')
        newd.cw_set(is_clone_of=self.d)
        self.commit()
        newd = self.session.entity_from_eid(newd.eid)
        self.assertEqual([u'Bottom -> Left -> Diamond (TopClone)',
                          u'Bottom -> Right -> Diamond (TopClone)',
                          u'Diamond (TopClone)',
                          u'Left -> Diamond (TopClone)',
                          u'Right -> Diamond (TopClone)'],
                         sorted([x.dc_title() for x in newd.reverse_diamond]))

    def test_container_relation_hook(self):
        session = self.session
        u = session.create_entity('NearTop', reverse_has_near_top=self.d)
        notinside = session.create_entity('EtypeNotInContainers',
                                          composite_but_not_in_diamond=self.l)
        session.commit()
        session = self.session
        notinside = session.entity_from_eid(notinside.eid)
        # notinside has a computable parent but no related container
        self.assertNone(notinside.cw_adapt_to('Container'))
        u = session.entity_from_eid(u.eid)
        self.assertEqual(self.d.eid, u.cw_adapt_to('Container').parent.eid)
        self.assertEqual(self.d.eid, u.cw_adapt_to('Container').related_container.eid)

    def test_container_rtype_hook(self):
        session = self.session
        self.assertEqual(5, len(session.execute('Any X,Y WHERE X diamond Y')))
        l = session.entity_from_eid(self.l.eid)
        self.assertEqual(self.d.eid, l.cw_adapt_to('Container').related_container.eid)
        self.assertEqual('Diamond', l.container_etype[0].name)
        self.assertEqual(l.eid, self.b1.cw_adapt_to('Container').parent.eid)
        self.assertEqual(self.r.eid, self.b2.cw_adapt_to('Container').parent.eid)

        m = session.create_entity('Mess')
        b3 = session.create_entity('Bottom', to_mess=m)
        # relocating through another rtype / to another container is forbiden
        with self.assertRaises(ValidationError) as wraperr:
            b3.cw_set(top_by_left=l)
        self.assertEqual({'top_by_left': u'Bottom is already in a container through top_by_left'},
                         wraperr.exception.args[1])
        session.rollback()

        session = self.session
        m = session.create_entity('Mess')
        self.assertRaises(ValidationError, session.create_entity,
                          'Bottom', to_mess=m, top_by_left=l)
        session.rollback()

        session = self.session
        i = session.create_entity('IAmAnAttributeCarryingRelation',
                              foo=42, to_left=l, to_right=self.r)
        session.commit()
        self.assertEqual(l.eid, i.to_left[0].eid)
        self.assertEqual(self.r.eid, i.to_right[0].eid)

    def test_relocate_to_other_parent(self):
        session = self.session
        b1 = session.entity_from_eid(self.b1.eid)
        self.assertEqual(self.l.eid, b1.cw_adapt_to('Container').parent.eid)
        l2 = session.create_entity('Left', top_from_left=self.d)
        session.commit()
        # relocate within same container/same rtype
        session = self.session
        b1 = session.entity_from_eid(self.b1.eid)
        self.assertEqual(self.l.eid, b1.cw_adapt_to('Container').parent.eid)
        b1.cw_set(top_by_left=l2.eid)
        self.assertEqual(l2.eid, b1.cw_adapt_to('Container').parent.eid)
        session.commit()
        # relocate within same container/different rtype
        session = self.session
        b1 = session.entity_from_eid(self.b1.eid)
        self.assertEqual(l2.eid, b1.cw_adapt_to('Container').parent.eid)
        with self.assertRaises(ValidationError) as wraperr:
            b1.cw_set(top_by_right=self.r.eid)
        self.assertEqual({'top_by_right': u'Bottom is already in a container through top_by_right'},
                         wraperr.exception.args[1])
        # relocate to different container/same rtype
        session = self.session
        b1 = session.entity_from_eid(self.b1.eid)
        d2 = session.create_entity('Diamond')
        l3 = session.create_entity('Left', top_from_left=d2)
        with self.assertRaises(ValidationError) as wraperr:
            b1.cw_set(top_by_left=l3)
        self.assertEqual({'top_by_left': u'Bottom is already in a container through top_by_left'},
                         wraperr.exception.args[1])

if __name__ == '__main__':
    unittest_main()
