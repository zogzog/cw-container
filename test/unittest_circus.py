from logilab.common.testlib import unittest_main

from cubicweb.devtools.testlib import CubicWebTC

from cubes.container import utils


class CircusTC(CubicWebTC):
    appid = 'data-circus'

    def test_static_structure(self):
        schema = self.vreg.schema
        diamond = self.vreg['etypes'].etype_class('Circus')
        rtypes, etypes = utils.container_static_structure(
            schema, 'Circus', 'circus', subcontainers=('Menagerie',))
        self.assertSetEqual(set(('Clown', 'ClownCabal', 'Joke', 'Menagerie')), etypes)
        self.assertSetEqual(set(('clowns', 'cabals', 'jokes', 'members', 'in_circus')), rtypes)
        rtypes, etypes = utils.container_static_structure(
            schema, 'Menagerie', 'zoo')
        self.assertEqual(set(['animals']), rtypes)
        self.assertEqual(set(['Animal']), etypes)

    def test_clown_in_cabal_not_in_circus(self):
        req = self.request()
        bozo = req.create_entity('Clown', name=u'Bozo')
        req.create_entity('Joke', content=u'funny', reverse_jokes=bozo)
        req.create_entity('ClownCabal', members=bozo)
        self.commit()

    def test_composite_subjrel_from_subcontainer_is_cloned(self):
        s = self.session
        u = s.create_entity('Umbrella')
        c = s.create_entity('Circus', reverse_has_circus=u)
        m = s.create_entity('Menagerie', in_circus=c)
        a = s.create_entity('Animal', reverse_animals=m, name=u'Babar')
        self.commit()

        s = self.session
        c = s.entity_from_eid(c.eid)
        self.assertEqual(c, c.circus[0])

        clone = s.create_entity('Circus')
        cloner = clone.cw_adapt_to('Container.clone')

        with s.deny_all_hooks_but(*cloner.config.compulsory_hooks_categories):
            cloner.clone(original=c.eid)
            self.commit()

        c2 = s.entity_from_eid(clone.eid)
        self.assertEqual(u'Babar', c2.reverse_in_circus[0].animals[0].name)


if __name__ == '__main__':
    unittest_main()
