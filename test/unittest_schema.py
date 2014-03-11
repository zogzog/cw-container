from logilab.common.testlib import unittest_main
from cubicweb.devtools.testlib import CubicWebTC

from cubes.container import ContainerConfiguration, utils, _needs_container_parent

class SchemaContainerTC(CubicWebTC):

    def test_needs_container_parent(self):
        schema = self.vreg.schema
        for etype in ('Diamond', 'Left', 'Right', 'Mess'):
            self.assertFalse(_needs_container_parent(schema[etype]))
        self.assertTrue(_needs_container_parent(schema['Bottom']))

    def test_static_structure_diamond(self):
        cfg = ContainerConfiguration('Diamond', 'diamond',
                                     skipetypes=('EtypeNotInContainers',))
        self.assertEqual((frozenset(['top_from_left', 'top_by_right',
                                     'top_from_right', 'top_by_left',
                                     'to_left', 'to_right', 'has_near_top']),
                          frozenset(['NearTop', 'Left', 'Right', 'Bottom',
                                     'IAmAnAttributeCarryingRelation'])),
                         cfg.structure(self.vreg.schema))


    def test_static_structure_left(self):
        cfg = ContainerConfiguration('Left', 'diamond',
                                     skipetypes=('EtypeNotInContainers',))
        self.assertEqual((frozenset(['to_left', 'top_by_left']),
                          frozenset(['Bottom', 'IAmAnAttributeCarryingRelation'])),
                         cfg.structure(self.vreg.schema))

    def test_static_structure_mess(self):
        cfg = ContainerConfiguration('Mess', 'in_mess',
                                     skiprtypes=('local_group', 'wf_info_for'))
        self.assertEqual((frozenset(['to_mess']), frozenset(['Bottom'])),
                         cfg.structure(self.vreg.schema))

    def test_inner_relations_diamond(self):
        cfg = ContainerConfiguration('Diamond', 'diamond',
                                     skipetypes=('EtypeNotInContainers',))
        self.assertEqual(frozenset(['loop_in_place', 'to_inner_left']),
                         set(cfg.inner_relations(self.vreg.schema)))

    def test_inner_relations_mess(self):
        cfg = ContainerConfiguration('Mess', 'in_mess',
                                     skiprtypes=('local_group', 'wf_info_for'))
        self.assertEqual(set(), set(cfg.inner_relations(self.vreg.schema)))

    def test_order_diamond(self):
        cfg = ContainerConfiguration('Diamond', 'diamond',
                                     skipetypes=('EtypeNotInContainers',))
        self.assertEqual(['Left', 'NearTop', 'Right', 'Bottom', 'IAmAnAttributeCarryingRelation'],
                         cfg._ordered_container_etypes(self.vreg.schema))

    def test_order_mess(self):
        cfg = ContainerConfiguration('Mess', 'in_mess',
                                     skiprtypes=('local_group', 'wf_info_for'))
        self.assertEqual(['Bottom'],
                         cfg._ordered_container_etypes(self.vreg.schema))

    def test_rtypes_for_hooks_diamond(self):
        cfg = ContainerConfiguration('Diamond', 'diamond',
                                     skipetypes=('EtypeNotInContainers',))
        schema = self.vreg.schema
        self.assertEqual({'top_by_right': set([('Bottom', 'Right')]),
                          'to_left': set([('IAmAnAttributeCarryingRelation', 'Left')]),
                          'to_right': set([('IAmAnAttributeCarryingRelation', 'Right')]),
                          'top_by_left': set([('Bottom', 'Left')])},
                         cfg._container_parent_rdefs(schema))
        self.assertEqual(frozenset(['to_right', 'to_left', 'top_by_right', 'top_by_left']),
                         utils.set_container_parent_rtypes_hook(schema, 'Diamond', 'diamond',
                                                                cfg.skiprtypes))

    def test_rtypes_for_hooks_mess(self):
        cfg = ContainerConfiguration('Mess', 'in_mess',
                                     skiprtypes=('local_group', 'wf_info_for'))
        schema = self.vreg.schema
        self.assertEqual({'to_mess': set([('Bottom', 'Mess')])},
                         cfg._container_parent_rdefs(schema))
        self.assertEqual(set(['to_mess']),
                         utils.set_container_parent_rtypes_hook(schema, 'Mess', 'in_mess',
                                                                cfg.skiprtypes))

if __name__ == '__main__':
    unittest_main()
