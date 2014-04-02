from logilab.common.testlib import unittest_main

from cubicweb.devtools.testlib import CubicWebTC

from cubes.container import CONTAINERS
from cubes.container.testutils import ContainerMixinTC


class CircusTC(ContainerMixinTC, CubicWebTC):
    appid = 'data-circus'

    def test_register(self):
        from config import CIRCUS_CONTAINER, MENAGERIE_CONTAINER
        self.assertEqual(CONTAINERS, {'Circus': CIRCUS_CONTAINER,
                                      'Menagerie': MENAGERIE_CONTAINER})

    def test_static_structure(self):
        from config import CIRCUS_CONTAINER, MENAGERIE_CONTAINER
        schema = self.vreg.schema
        diamond = self.vreg['etypes'].etype_class('Circus')
        rtypes, etypes = CIRCUS_CONTAINER.structure(schema)
        self.assertEqual(set(('Clown', 'ClownCabal', 'Joke', 'Menagerie',
                              'Costume')), etypes)
        self.assertEqual(set(('clowns', 'cabals', 'jokes', 'members',
                              'in_circus', 'costume', 'costumes')), rtypes)
        strict_etypes = CIRCUS_CONTAINER.structure(self.schema, strict=True)[1]
        self.assertEqual(strict_etypes, set(['Costume']))
        rtypes, etypes = MENAGERIE_CONTAINER.structure(schema)
        self.assertEqual(set(['animals']), rtypes)
        self.assertEqual(set(['Animal']), etypes)

    def test_clown_in_cabal_not_in_circus(self):
        req = self.request()
        bozo = req.create_entity('Clown', name=u'Bozo')
        req.create_entity('Joke', content=u'funny', reverse_jokes=bozo)
        cabal = req.create_entity('ClownCabal', members=bozo)
        self.commit()
        circus = req.create_entity('Circus', cabals=cabal)
        self.commit()
        self.assertEqual(circus.eid, cabal.circus[0].eid)
        bozo.cw_clear_all_caches()
        self.assertEqual(circus.eid, bozo.circus[0].eid)

    def test_clown_in_two_cabals(self):
        req = self.request()
        bozo = req.create_entity('Clown', name=u'Bozo')
        cabal = req.create_entity('ClownCabal', members=bozo)
        self.commit()
        bozo.cw_clear_all_caches()
        self.assertEqual(bozo.container_parent[0].eid, cabal.eid)
        othercabal = req.create_entity('ClownCabal', members=bozo)
        self.commit()
        bozo.cw_clear_all_caches()
        self.assertEqual(bozo.container_parent[0].eid, othercabal.eid)

    def test_composite_subjrel_from_subcontainer_is_cloned(self):
        s = self.session
        c = s.create_entity('Circus')
        m = s.create_entity('Menagerie', in_circus=c)
        a = s.create_entity('Animal', reverse_animals=m, name=u'Babar')
        self.commit()

        clone = s.create_entity('Circus')
        cloner = clone.cw_adapt_to('Container.clone')

        with s.deny_all_hooks_but(*cloner.compulsory_hooks_categories):
            cloner.clone(original=c.eid)
            self.commit()

        c2 = s.entity_from_eid(clone.eid)
        self.assertEqual(u'Babar', c2.reverse_in_circus[0].animals[0].name)


if __name__ == '__main__':
    unittest_main()
