from logilab.common.testlib import unittest_main
from cubicweb import ValidationError
from cubicweb.devtools.testlib import CubicWebTC

class ContainerEntitiesTC(CubicWebTC):

    def setup_database(self):
        req = self.request()
        self.d = req.create_entity('Diamond')
        self.l = req.create_entity('Left', top_from_left=self.d)
        self.assertEqual(self.l.cw_adapt_to('Container').related_container.eid, self.d.eid)
        self.r = req.create_entity('Right', top_from_right=self.d, to_inner_left=self.l)
        self.b1 = req.create_entity('Bottom', top_by_left=self.l)
        self.b2 = req.create_entity('Bottom', top_by_right=self.r)

    def test_container_rtype_hook(self):
        self.assertEqual(len(self.execute('Any X,Y WHERE X diamond Y')), 4)
        req = self.request()
        l = req.entity_from_eid(self.l.eid)
        self.assertEqual(l.cw_adapt_to('Container').related_container.eid, self.d.eid)
        self.assertEqual(l.container_etype[0].name, 'Diamond')
        self.assertEqual(self.b1.cw_adapt_to('Container').parent.eid, l.eid)
        self.assertEqual(self.b2.cw_adapt_to('Container').parent.eid, self.r.eid)

        req = self.request()
        m = req.create_entity('Mess')
        b3 = req.create_entity('Bottom', to_mess=m)
        # relocating through another rtype / to another container is forbiden
        self.assertRaises(ValidationError, b3.set_relations, top_by_left=l)
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
        self.assertEqual(i.to_left[0].eid, l.eid)
        self.assertEqual(i.to_right[0].eid, self.r.eid)

    def test_relocate_to_other_parent(self):
        req = self.request()
        b1 = req.entity_from_eid(self.b1.eid)
        self.assertEqual(b1.cw_adapt_to('Container').parent.eid, self.l.eid)
        l2 = req.create_entity('Left', top_from_left=self.d)
        self.commit()
        # relocate within same container/same rtype
        req = self.request()
        b1 = req.entity_from_eid(self.b1.eid)
        self.assertEqual(b1.cw_adapt_to('Container').parent.eid, self.l.eid)
        b1.set_relations(top_by_left=l2.eid)
        self.assertEqual(b1.cw_adapt_to('Container').parent.eid, self.l.eid) # still
        self.commit()
        # relocate within same container/different rtype
        req = self.request()
        b1 = req.entity_from_eid(self.b1.eid)
        self.assertEqual(b1.cw_adapt_to('Container').parent.eid, l2.eid)
        self.assertRaises(ValidationError, b1.set_relations, top_by_right=self.r.eid)
        # relocate to different container/same rtype
        req = self.request()
        b1 = req.entity_from_eid(self.b1.eid)
        d2 = req.create_entity('Diamond')
        l3 = req.create_entity('Left', top_from_left=d2)
        self.assertRaises(ValidationError, b1.set_relations, top_by_left=l3)

if __name__ == '__main__':
    unittest_main()
