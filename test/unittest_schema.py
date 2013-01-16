from logilab.common.testlib import unittest_main
from cubicweb.devtools.testlib import CubicWebTC

from cubes.container import utils

class SchemaContainerTC(CubicWebTC):

    def test_needs_container_parent(self):
        schema = self.vreg.schema
        for etype in ('Diamond', 'Left', 'Right', 'Mess'):
            self.assertFalse(utils.needs_container_parent(schema[etype]))
        self.assertTrue(utils.needs_container_parent(schema['Bottom']))

    def test_static_structure(self):
        schema = self.vreg.schema
        diamond = self.vreg['etypes'].etype_class('Diamond')
        mess = self.vreg['etypes'].etype_class('Mess')
        self.assertEqual(utils.container_static_structure(schema, 'Diamond', 'diamond',
                                                          diamond.container_skiprtypes),
                         (frozenset(['top_from_left', 'top_by_right', 'top_from_right', 'top_by_left',
                                     'to_left', 'to_right']),
                          frozenset(['Left', 'Right', 'Bottom', 'IAmAnAttributeCarryingRelation'])))

        self.assertEqual(utils.container_static_structure(schema, 'Left', 'diamond'),
                         (frozenset(['to_left', 'top_by_left']),
                          frozenset(['Bottom', 'IAmAnAttributeCarryingRelation'])))

        self.assertEqual(utils.container_static_structure(schema, 'Mess', 'in_mess',
                                                          mess.container_skiprtypes),
                         (frozenset(['to_mess']), frozenset(['Bottom'])))

    def test_etypes_rtypes(self):
        schema = self.vreg.schema
        diamond = self.vreg['etypes'].etype_class('Diamond')
        mess = self.vreg['etypes'].etype_class('Mess')
        self.assertEqual(utils.container_rtypes_etypes(schema, 'Diamond', 'diamond',
                                                       diamond.container_skiprtypes),
                         (frozenset(['to_inner_left', 'top_from_left', 'top_by_right',
                                     'top_from_right', 'top_by_left', 'loop_in_place',
                                     'to_left', 'to_right']),
                          frozenset(['Left', 'Right', 'Bottom', 'IAmAnAttributeCarryingRelation'])))
        self.assertEqual(utils.container_rtypes_etypes(schema, 'Mess', 'in_mess',
                                                       mess.container_skiprtypes),
                         (frozenset(['to_mess']), frozenset(['Bottom'])))

    def test_order(self):
        schema = self.vreg.schema
        diamond = self.vreg['etypes'].etype_class('Diamond')
        mess = self.vreg['etypes'].etype_class('Mess')
        self.assertEqual(utils.ordered_container_etypes(schema, 'Diamond', 'diamond',
                                                        diamond.container_skiprtypes),
                         ['Left', 'Right', 'Bottom', 'IAmAnAttributeCarryingRelation'])
        self.assertEqual(utils.ordered_container_etypes(schema, 'Mess', 'in_mess',
                                                    mess.container_skiprtypes),
                         ['Bottom'])

    def test_rtypes_for_hooks(self):
        schema = self.vreg.schema
        diamond = self.vreg['etypes'].etype_class('Diamond')
        mess = self.vreg['etypes'].etype_class('Mess')
        self.assertEqual(frozenset(['to_right', 'to_left', 'top_by_right', 'top_by_left']),
                         utils.set_container_parent_rtypes_hook(schema, 'Diamond', 'diamond',
                                                                diamond.container_skiprtypes))
        self.assertEqual(frozenset(['top_from_left', 'top_from_right']),
                         utils.set_container_relation_rtypes_hook(schema, 'Diamond', 'diamond',
                                                                  diamond.container_skiprtypes))
        self.assertEqual(set(['to_mess']),
                         utils.set_container_parent_rtypes_hook(schema, 'Mess', 'in_mess',
                                                                diamond.container_skiprtypes))
        self.assertEqual(set(),
                         utils.set_container_relation_rtypes_hook(schema, 'Mess', 'in_mess',
                                                                  mess.container_skiprtypes))

if __name__ == '__main__':
    unittest_main()
