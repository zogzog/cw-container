from cubicweb import ValidationError
from cubicweb.devtools.testlib import CubicWebTC

class ContainerEntitiesTC(CubicWebTC):

    def test_container_rtype_hook(self):
        req = self.request()
        d = req.create_entity('Diamond')
        l = req.create_entity('Left', top_from_left=d)
        self.assertEqual(l.cw_adapt_to('Container').related_container.eid, d.eid)
        r = req.create_entity('Right', top_from_right=d, to_inner_left=l)
        b1 = req.create_entity('Bottom', top_by_left=l)
        b2 = req.create_entity('Bottom', top_by_right=r)
        self.commit()

        self.assertEqual(len(self.execute('Any X,Y WHERE X diamond Y')), 4)
        req = self.request()
        l = req.entity_from_eid(l.eid)
        self.assertEqual(l.cw_adapt_to('Container').related_container.eid, d.eid)
        self.assertEqual(l.container_etype[0].name, 'Diamond')
        self.assertEqual(b1.container_parent[0].eid, l.eid)
        self.assertEqual(b2.container_parent[0].eid, r.eid)

        req = self.request()
        m = req.create_entity('Mess')
        b3 = req.create_entity('Bottom', to_mess=m)
        self.assertRaises(ValidationError, b3.set_relations, top_by_left=l)
        self.rollback()

        req = self.request()
        m = req.create_entity('Mess')
        self.assertRaises(ValidationError, req.create_entity,
                          'Bottom', to_mess=m, top_by_left=l)
        self.rollback()

        req = self.request()
        i = req.create_entity('IAmAnAttributeCarryingRelation',
                              foo=42, to_left=l, to_right=r)
        self.commit()
        self.assertEqual(i.to_left[0].eid, l.eid)
        self.assertEqual(i.to_right[0].eid, r.eid)
