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
        self.assertEqual((frozenset(['top_from_left', 'top_by_right', 'top_from_right', 'top_by_left',
                                     'to_left', 'to_right', 'has_near_top']),
                          frozenset(['NearTop', 'Left', 'Right', 'Bottom', 'IAmAnAttributeCarryingRelation'])),
                         utils.container_static_structure(schema, 'Diamond', 'diamond',
                                                          skiprtypes=diamond.container_skiprtypes,
                                                          skipetypes=diamond.container_skipetypes))

        self.assertEqual((frozenset(['to_left', 'top_by_left']),
                          frozenset(['Bottom', 'IAmAnAttributeCarryingRelation'])),
                         utils.container_static_structure(schema, 'Left', 'diamond',
                                                          skipetypes=diamond.container_skipetypes))

        self.assertEqual((frozenset(['to_mess']), frozenset(['Bottom'])),
                         utils.container_static_structure(schema, 'Mess', 'in_mess',
                                                          mess.container_skiprtypes))

    def test_etypes_rtypes(self):
        schema = self.vreg.schema
        diamond = self.vreg['etypes'].etype_class('Diamond')
        mess = self.vreg['etypes'].etype_class('Mess')
        self.assertEqual((frozenset(['to_inner_left', 'top_from_left', 'top_by_right',
                                     'top_from_right', 'top_by_left', 'loop_in_place',
                                     'to_left', 'to_right', 'has_near_top']),
                          frozenset(['NearTop', 'Left', 'Right', 'Bottom',
                                     'IAmAnAttributeCarryingRelation'])),
                         utils.container_rtypes_etypes(schema, 'Diamond', 'diamond',
                                                       skiprtypes=diamond.container_skiprtypes,
                                                       skipetypes=diamond.container_skipetypes))
        self.assertEqual((frozenset(['to_mess']), frozenset(['Bottom'])),
                         utils.container_rtypes_etypes(schema, 'Mess', 'in_mess',
                                                       mess.container_skiprtypes))

    def test_order(self):
        schema = self.vreg.schema
        diamond = self.vreg['etypes'].etype_class('Diamond')
        mess = self.vreg['etypes'].etype_class('Mess')
        self.assertEqual(['Left', 'NearTop', 'Right', 'Bottom', 'IAmAnAttributeCarryingRelation'],
                         utils.ordered_container_etypes(schema, 'Diamond', 'diamond',
                                                        skiprtypes=diamond.container_skiprtypes,
                                                        skipetypes=diamond.container_skipetypes))
        self.assertEqual(['Bottom'],
                         utils.ordered_container_etypes(schema, 'Mess', 'in_mess',
                                                        mess.container_skiprtypes))

    def test_rtypes_for_hooks(self):
        schema = self.vreg.schema
        diamond = self.vreg['etypes'].etype_class('Diamond')
        mess = self.vreg['etypes'].etype_class('Mess')
        self.assertEqual(frozenset(['to_right', 'to_left', 'top_by_right', 'top_by_left']),
                         utils.set_container_parent_rtypes_hook(schema, 'Diamond', 'diamond',
                                                                diamond.container_skiprtypes))
        self.assertEqual({'top_by_right': set([('Bottom', 'Right')]),
                          'to_left': set([('IAmAnAttributeCarryingRelation', 'Left')]),
                          'to_right': set([('IAmAnAttributeCarryingRelation', 'Right')]),
                          'top_by_left': set([('Bottom', 'Left')])},
                         utils.container_parent_rdefs(schema, 'Diamond', 'diamond',
                                                      diamond.container_skiprtypes))
        self.assertEqual(frozenset(['top_from_left', 'top_from_right', 'has_near_top',
                                    'to_right', 'to_left', 'top_by_right', 'top_by_left']),
                         utils.set_container_relation_rtypes_hook(schema, 'Diamond', 'diamond',
                                                                  skiprtypes=diamond.container_skiprtypes,
                                                                  skipetypes=diamond.container_skipetypes))


        self.assertEqual({'to_mess': set([('Bottom', 'Mess')])},
                         utils.container_parent_rdefs(schema, 'Mess', 'in_mess',
                                                      diamond.container_skiprtypes))
        self.assertEqual(set(['to_mess']),
                         utils.set_container_parent_rtypes_hook(schema, 'Mess', 'in_mess',
                                                                diamond.container_skiprtypes))
        self.assertEqual(set(('to_mess',)),
                         utils.set_container_relation_rtypes_hook(schema, 'Mess', 'in_mess',
                                                                  mess.container_skiprtypes))

if __name__ == '__main__':
    unittest_main()
