from logilab.common.testlib import unittest_main
from cubicweb.devtools.testlib import CubicWebTC

from cubes.container import utils, config
from cubes.container.testutils import rdefrepr

class SchemaContainerTC(CubicWebTC):

    def test_needs_container_parent(self):
        schema = self.vreg.schema
        for etype in ('Diamond', 'Left', 'Right', 'Mess'):
            self.assertFalse(utils.needs_container_parent(schema[etype]))
        self.assertTrue(utils.needs_container_parent(schema['Bottom']))

    def test_utils(self):
        schema = self.vreg.schema
        for etype, expected in (('Diamond',
                                 [('has_near_top', 'Diamond', 'NearTop'),
                                  ('top_from_left', 'Left', 'Diamond'),
                                  ('top_from_right', 'Right', 'Diamond')]),
                                ('NearTop', []),
                                ('IAmAnAttributeCarryingRelation', []),
                                ('Left',
                                 [('to_left', 'IAmAnAttributeCarryingRelation', 'Left'),
                                  ('top_by_left', 'Bottom', 'Left'),
                                  ('composite_but_not_in_diamond', 'EtypeNotInContainers', 'Left')]),
                                ('Right',
                                 [('to_right', 'IAmAnAttributeCarryingRelation', 'Right'),
                                  ('top_by_right', 'Bottom', 'Right')]),
                                ('Bottom', [])):
            self.assertEqual(expected,
                             [rdefrepr(rdef) for rdef in utils.children_rdefs(schema[etype])])

    def test_static_structure(self):
        schema = self.vreg.schema
        diamond = config.Container.by_etype('Diamond')
        mess = config.Container.by_etype('Mess')


        self.assertEqual(set([('to_right', 'IAmAnAttributeCarryingRelation', 'Right'),
                              ('top_from_right', 'Right', 'Diamond'),
                              ('top_by_right', 'Bottom', 'Right'),
                              ('to_left', 'IAmAnAttributeCarryingRelation', 'Left'),
                              ('has_near_top', 'Diamond', 'NearTop'),
                              ('top_from_left', 'Left', 'Diamond'),
                              ('top_by_left', 'Bottom', 'Left')]),
                         set([rdefrepr(rdef) for rdef in diamond.rdefs]))

        self.assertEqual(set([('to_mess', 'Bottom', 'Mess')]),
                         set([rdefrepr(rdef) for rdef in mess.rdefs]))

        # bw compat
        self.assertEqual((frozenset(['top_from_left', 'top_by_right', 'top_from_right', 'top_by_left',
                                     'to_left', 'to_right', 'has_near_top']),
                          frozenset(['NearTop', 'Left', 'Right', 'Bottom', 'IAmAnAttributeCarryingRelation'])),
                         utils.container_static_structure(schema, 'Diamond', 'diamond',
                                                          skiprtypes=diamond.skiprtypes,
                                                          skipetypes=diamond.skipetypes))

        self.assertEqual((frozenset(['to_left', 'top_by_left']),
                          frozenset(['Bottom', 'IAmAnAttributeCarryingRelation'])),
                         utils.container_static_structure(schema, 'Left', 'diamond',
                                                          skipetypes=diamond.skipetypes))

        self.assertEqual((frozenset(['to_mess']), frozenset(['Bottom'])),
                         utils.container_static_structure(schema, 'Mess', 'in_mess',
                                                          mess.skiprtypes))

    def test_etypes_rtypes(self):
        schema = self.vreg.schema
        diamond = config.Container.by_etype('Diamond')
        mess = config.Container.by_etype('Mess')

        self.assertEqual(frozenset(['to_inner_left', 'top_from_left', 'top_by_right',
                                    'top_from_right', 'top_by_left', 'loop_in_place',
                                    'to_left', 'to_right', 'has_near_top']),
                         set(rdef.rtype.type
                             for rdef in diamond.inner_rdefs))

        self.assertEqual(frozenset(['Diamond', 'NearTop', 'Left', 'Right', 'Bottom',
                                    'IAmAnAttributeCarryingRelation']),
                         diamond.etypes)

        self.assertEqual(frozenset(['to_mess']),
                         set(rdef.rtype.type
                           for rdef in mess.inner_rdefs))
        self.assertEqual(frozenset(['Mess', 'Bottom']), mess.etypes)

        # bw compat
        self.assertEqual((frozenset(['to_inner_left', 'top_from_left', 'top_by_right',
                                     'top_from_right', 'top_by_left', 'loop_in_place',
                                     'to_left', 'to_right', 'has_near_top']),
                          frozenset(['NearTop', 'Left', 'Right', 'Bottom',
                                     'IAmAnAttributeCarryingRelation'])),
                         utils.container_rtypes_etypes(schema, 'Diamond', 'diamond',
                                                       skiprtypes=diamond.skiprtypes,
                                                       skipetypes=diamond.skipetypes))
        self.assertEqual((frozenset(['to_mess']), frozenset(['Bottom'])),
                         utils.container_rtypes_etypes(schema, 'Mess', 'in_mess',
                                                       mess.skiprtypes))

    def test_order(self):
        schema = self.vreg.schema
        diamond = config.Container.by_etype('Diamond')
        mess = config.Container.by_etype('Mess')
        self.assertEqual(['Left', 'NearTop', 'Right', 'Bottom', 'IAmAnAttributeCarryingRelation'],
                         utils.ordered_container_etypes(schema, 'Diamond', 'diamond',
                                                        skiprtypes=diamond.skiprtypes,
                                                        skipetypes=diamond.skipetypes))
        self.assertEqual(['Bottom'],
                         utils.ordered_container_etypes(schema, 'Mess', 'in_mess',
                                                        mess.skiprtypes))

    def test_rtypes_for_hooks(self):
        schema = self.vreg.schema
        diamond = config.Container.by_etype('Diamond')
        mess = config.Container.by_etype('Mess')
        self.assertEqual(frozenset(['to_right', 'to_left', 'top_by_right', 'top_by_left']),
                         utils.set_container_parent_rtypes_hook(schema, 'Diamond', 'diamond',
                                                                diamond.skiprtypes))
        self.assertEqual({'top_by_right': set([('Bottom', 'Right')]),
                          'to_left': set([('IAmAnAttributeCarryingRelation', 'Left')]),
                          'to_right': set([('IAmAnAttributeCarryingRelation', 'Right')]),
                          'top_by_left': set([('Bottom', 'Left')])},
                         utils.container_parent_rdefs(schema, 'Diamond', 'diamond',
                                                      diamond.skiprtypes))
        self.assertEqual(frozenset(['top_from_left', 'top_from_right', 'has_near_top',
                                    'to_right', 'to_left', 'top_by_right', 'top_by_left']),
                         utils.set_container_relation_rtypes_hook(schema, 'Diamond', 'diamond',
                                                                  skiprtypes=diamond.skiprtypes,
                                                                  skipetypes=diamond.skipetypes))


        self.assertEqual({'to_mess': set([('Bottom', 'Mess')])},
                         utils.container_parent_rdefs(schema, 'Mess', 'in_mess',
                                                      diamond.skiprtypes))
        self.assertEqual(set(['to_mess']),
                         utils.set_container_parent_rtypes_hook(schema, 'Mess', 'in_mess',
                                                                diamond.skiprtypes))
        self.assertEqual(set(('to_mess',)),
                         utils.set_container_relation_rtypes_hook(schema, 'Mess', 'in_mess',
                                                                  mess.skiprtypes))

if __name__ == '__main__':
    unittest_main()
