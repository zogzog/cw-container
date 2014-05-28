from logilab.common.testlib import unittest_main
from cubicweb import ValidationError
from cubicweb.devtools.testlib import CubicWebTC

from cubes.container.testutils import ContainerMixinTC


class ContainerLessTC(ContainerMixinTC, CubicWebTC):

    def test_free_from_container(self):
        l = self.request().create_entity('Left')
        self.assertIsNone(l.cw_adapt_to('Container').related_container)
        self.assertIsNone(l.cw_adapt_to('Container').parent)
        self.commit()
        self.assertIsNone(l.cw_adapt_to('Container').related_container)
        self.assertIsNone(l.cw_adapt_to('Container').parent)

    def test_adapter_without_container(self):
        u = self.request().execute('CWUser U WHERE U login "admin"').get_entity(0,0)
        adapter = u.cw_adapt_to('Container')
        self.assertIsNone(adapter)


class ContainerEntitiesTC(ContainerMixinTC, CubicWebTC):

    def setup_database(self):
        req = self.request()
        self.d = req.create_entity('Diamond')
        self.l = req.create_entity('Left', top_from_left=self.d)
        self.assertEqual(self.d.eid, self.l.cw_adapt_to('Container').related_container.eid)
        self.r = req.create_entity('Right', top_from_right=self.d, to_inner_left=self.l)
        self.b1 = req.create_entity('Bottom', top_by_left=self.l)
        self.b2 = req.create_entity('Bottom', top_by_right=self.r)

    def test_clone_entry_point(self):
        req = self.session
        newd = req.create_entity('Diamond')
        cloner = newd.cw_adapt_to('Container.clone')
        self.assertRaises(TypeError, cloner.clone)
        self.assertRaises(TypeError, cloner.clone, original=newd)
        cloner.clone(original=newd.eid)
        self.commit()

    def test_container_relation_hook(self):
        req = self.request()
        u = req.create_entity('NearTop', reverse_has_near_top=self.d)
        notinside = req.create_entity('EtypeNotInContainers',
                                      composite_but_not_in_diamond=self.l)
        self.commit()
        req = self.request()
        notinside = req.entity_from_eid(notinside.eid)
        self.assertIsNone(notinside.cw_adapt_to('Container'))
        u = req.entity_from_eid(u.eid)
        self.assertEqual(self.d.eid, u.cw_adapt_to('Container').parent.eid)
        self.assertEqual(self.d.eid, u.cw_adapt_to('Container').related_container.eid)

    def test_container_rtype_hook(self):
        self.assertEqual(4, len(self.execute('Any X,Y WHERE X diamond Y')))
        req = self.request()
        l = req.entity_from_eid(self.l.eid)
        self.assertEqual(self.d.eid, l.cw_adapt_to('Container').related_container.eid)
        self.assertEqual('Diamond', l.container_etype[0].name)
        self.assertEqual(l.eid, self.b1.cw_adapt_to('Container').parent.eid)
        self.assertEqual(self.r.eid, self.b2.cw_adapt_to('Container').parent.eid)

        req = self.request()
        m = req.create_entity('Mess')
        b3 = req.create_entity('Bottom', to_mess=m)
        # relocating through another rtype / to another container is forbiden
        with self.assertRaises(ValidationError) as wraperr:
            b3.cw_set(top_by_left=l)
        self.assertEqual({'top_by_left': u'Bottom is already in a container through top_by_left'},
                         wraperr.exception.args[1])
        self.rollback()

        req = self.request()
        m = req.create_entity('Mess')
        self.assertRaises(ValidationError, req.create_entity,
                          'Bottom', to_mess=m, top_by_left=l)
        self.rollback()

        req = self.request()
        i = req.create_entity('IAmAnAttributeCarryingRelation',
                              foo=42, to_left=l, to_right=self.r)
        self.commit()
        self.assertEqual(l.eid, i.to_left[0].eid)
        self.assertEqual(self.r.eid, i.to_right[0].eid)

    def test_relocate_to_other_parent(self):
        req = self.request()
        b1 = req.entity_from_eid(self.b1.eid)
        self.assertEqual(self.l.eid, b1.cw_adapt_to('Container').parent.eid)
        l2 = req.create_entity('Left', top_from_left=self.d)
        self.commit()
        # relocate within same container/same rtype
        req = self.request()
        b1 = req.entity_from_eid(self.b1.eid)
        self.assertEqual(self.l.eid, b1.cw_adapt_to('Container').parent.eid)
        b1.cw_set(top_by_left=l2.eid)
        self.assertEqual(self.l.eid, b1.cw_adapt_to('Container').parent.eid) # still
        self.commit()
        # relocate within same container/different rtype
        req = self.request()
        b1 = req.entity_from_eid(self.b1.eid)
        self.assertEqual(l2.eid, b1.cw_adapt_to('Container').parent.eid)
        with self.assertRaises(ValidationError) as wraperr:
            b1.cw_set(top_by_right=self.r.eid)
        self.assertEqual({'top_by_right': u'Bottom is already in a container through top_by_right'},
                         wraperr.exception.args[1])
        # relocate to different container/same rtype
        req = self.request()
        b1 = req.entity_from_eid(self.b1.eid)
        d2 = req.create_entity('Diamond')
        l3 = req.create_entity('Left', top_from_left=d2)
        with self.assertRaises(ValidationError) as wraperr:
            b1.cw_set(top_by_left=l3)
        self.assertEqual({'top_by_left': u'Bottom is already in a container through top_by_left'},
                         wraperr.exception.args[1])

if __name__ == '__main__':
    unittest_main()
