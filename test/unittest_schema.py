from logilab.common.testlib import unittest_main
from cubicweb.devtools.testlib import CubicWebTC

from cubes.container import (ContainerConfiguration, utils,
                             _needs_container_parent, CONTAINERS)
from cubes.container.testutils import (ContainerMixinTC,
                                       rtypes_etypes_not_in_container)


class SchemaContainerTC(ContainerMixinTC, CubicWebTC):

    def test_needs_container_parent(self):
        schema = self.vreg.schema
        for etype in ('Diamond', 'Left', 'Right', 'Mess'):
            self.assertFalse(_needs_container_parent(schema[etype]))
        self.assertTrue(_needs_container_parent(schema['Bottom']))

    def test_static_structure_diamond(self):
        cfg = self.replace_config('Diamond', 'diamond',
                                  skipetypes=('EtypeNotInContainers',))
        self.assertEqual((frozenset(['top_from_left', 'top_by_right',
                                     'top_from_right', 'top_by_left',
                                     'to_left', 'to_right', 'has_near_top']),
                          frozenset(['NearTop', 'Left', 'Right', 'Bottom',
                                     'IAmAnAttributeCarryingRelation'])),
                         cfg.structure(self.vreg.schema))
        strict_etypes = cfg.structure(self.vreg.schema, strict=True)[1]
        self.assertEqual(strict_etypes, set(['Right']))

    def test_static_structure_left(self):
        cfg = ContainerConfiguration('Left', 'diamond',
                                     skipetypes=('EtypeNotInContainers',))
        self.assertEqual((frozenset(['to_left', 'top_by_left']),
                          frozenset(['Bottom', 'IAmAnAttributeCarryingRelation'])),
                         cfg.structure(self.vreg.schema))
        strict_etypes = cfg.structure(self.vreg.schema, strict=True)[1]
        self.assertEqual(strict_etypes, set())

    def test_static_structure_mess(self):
        cfg = self.replace_config('Mess', 'in_mess',
                                  skiprtypes=('local_group', 'wf_info_for'))
        self.assertEqual((frozenset(['to_mess']), frozenset(['Bottom'])),
                         cfg.structure(self.vreg.schema))
        strict_etypes = cfg.structure(self.schema, strict=True)[1]
        self.assertEqual(strict_etypes, set())

    def test_inner_relations_diamond(self):
        cfg = self.replace_config('Diamond', 'diamond',
                                  skipetypes=('EtypeNotInContainers',))
        self.assertEqual(frozenset(['loop_in_place', 'to_inner_left']),
                         set(cfg.inner_relations(self.vreg.schema)))

    def test_inner_relations_mess(self):
        cfg = self.replace_config('Mess', 'in_mess',
                                  skiprtypes=('local_group', 'wf_info_for'))
        self.assertEqual(set(), set(cfg.inner_relations(self.vreg.schema)))

    def test_rtypes_for_hooks_diamond(self):
        cfg = self.replace_config('Diamond', 'diamond',
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
        cfg = self.replace_config('Mess', 'in_mess',
                                  skiprtypes=('local_group', 'wf_info_for'))
        schema = self.vreg.schema
        self.assertEqual({'to_mess': set([('Bottom', 'Mess')])},
                         cfg._container_parent_rdefs(schema))
        self.assertEqual(set(['to_mess']),
                         utils.set_container_parent_rtypes_hook(schema, 'Mess', 'in_mess',
                                                                cfg.skiprtypes))

    def test_etypes_rtypes_not_in_container(self):
        # Entity types and relation types defined in CW and present in any
        # schema.
        cw_ignore_rtypes = ('bookmarked_by', 'primary_email', 'use_email',
                            'prefered_form')
        cw_ignore_etypes = ('EmailAddress', 'CWGroup', 'Bookmark', 'CWUser')
        diamond_cfg = self.replace_config(
            'Diamond', 'diamond', skipetypes=('EtypeNotInContainers',))
        rtypes, etypes = rtypes_etypes_not_in_container(
            self.vreg.schema, diamond_cfg)
        self.set_description('diamond: rtypes not in container')
        yield self.assertCountEqual, rtypes, cw_ignore_rtypes + (
            'watcher', 'composite_but_not_in_diamond',
            'linked_to_mess', 'to_mess', 'local_group')
        self.set_description('diamond: etypes not in container')
        yield self.assertCountEqual, etypes, cw_ignore_etypes + (
            'Diamond', 'Mess', 'EtypeNotInContainers')
        mess_cfg = self.replace_config(
            'Mess', 'in_mess', skiprtypes=('local_group', 'wf_info_for'))
        rtypes, etypes = rtypes_etypes_not_in_container(
            self.vreg.schema, mess_cfg)
        self.set_description('mess: rtypes not in container')
        yield self.assertCountEqual, rtypes, cw_ignore_rtypes + (
            'to_left', 'to_inner_left', 'top_by_right', 'watcher',
            'composite_but_not_in_diamond', 'top_by_left', 'loop_in_place',
            'has_near_top', 'to_right', 'local_group', 'top_from_left',
            'top_from_right', 'linked_to_mess')
        self.set_description('mess: etypes not in container')
        yield self.assertCountEqual, etypes, cw_ignore_etypes + (
            'Mess', 'EtypeNotInContainers',
            'Diamond', 'NearTop', 'Right', 'Left',
            'IAmAnAttributeCarryingRelation')

    def test_order_diamond(self):
        cloner = self.request().create_entity('Diamond').cw_adapt_to('Container.clone')
        self.assertEqual(['Left', 'NearTop', 'Right', 'Bottom', 'IAmAnAttributeCarryingRelation'],
                         cloner._ordered_container_etypes())

    def test_order_mess(self):
        cloner = self.request().create_entity('Mess').cw_adapt_to('Container.clone')
        self.assertEqual(['Bottom'],
                         cloner._ordered_container_etypes())

if __name__ == '__main__':
    unittest_main()
