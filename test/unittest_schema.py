from logilab.common.testlib import unittest_main
from cubicweb.devtools import testlib

from cubes.container import utils, config
from cubes.container.testutils import rdefrepr

class SchemaContainerTC(testlib.CubicWebTC):

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

    def test_parent_rschemas(self):
        schema = self.schema
        for etype, expected in (('Diamond', []),
                                ('Left', [('top_from_left', 'subject')]),
                                ('Bottom', [('to_mess', 'subject'),
                                            ('top_by_left', 'subject'),
                                            ('top_by_right', 'subject')]),
                                ('Mess', [])):
            self.assertEqual(expected,
                             sorted([(e.type, role)
                                     for e, role in utils.parent_rschemas(schema[etype])]))

    def test_static_structure(self):
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

    def test_etypes_rtypes(self):
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


if __name__ == '__main__':
    unittest_main()
