from cubicweb.devtools.testlib import CubicWebTC

from cubes.container import utils

class SchemaContainerTC(CubicWebTC):

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
        self.assertEqual(utils.ordered_container_etypes(schema, 'Diamond', 'diamond'),
                         ['IAmAnAttributeCarryingRelation', 'Right', 'Left', 'Bottom'])
        self.assertEqual(utils.ordered_container_etypes(schema, 'Mess', 'in_mess'),
                         ['CWGroup', 'Bottom'])
