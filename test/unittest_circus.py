from logilab.common.testlib import unittest_main

from cubicweb.devtools.testlib import CubicWebTC

from cubes.container import config


class CircusTC(CubicWebTC):
    appid = 'data-circus'

    def test_static_structure(self):
        conf = config.Container.by_etype('Circus')
        self.assertSetEqual(set(('Circus', 'Clown', 'ClownCabal', 'Joke', 'Menagerie')),
                            conf.etypes)
        self.assertSetEqual(set(('clowns', 'cabals', 'jokes', 'members', 'in_circus')),
                            set(rdef.rtype.type for rdef in conf.inner_rdefs))

    def test_clown_in_cabal_not_in_circus(self):
        with self.admin_access.repo_cnx() as cnx:
            bozo = cnx.create_entity('Clown', name=u'Bozo')
            cnx.create_entity('Joke', content=u'funny', reverse_jokes=bozo)
            cnx.create_entity('ClownCabal', members=bozo)
            cnx.commit()

    def test_composite_subjrel_from_subcontainer_is_cloned(self):
        with self.admin_access.repo_cnx() as cnx:
            u = cnx.create_entity('Umbrella')
            c = cnx.create_entity('Circus', reverse_has_circus=u)
            m = cnx.create_entity('Menagerie', in_circus=c)
            a = cnx.create_entity('Animal', reverse_animals=m, name=u'Babar')
            cnx.commit()

            c = cnx.entity_from_eid(c.eid)
            self.assertEqual(c, c.circus[0])

            clone = cnx.create_entity('Circus')
            cloner = clone.cw_adapt_to('Container.clone')

            with cnx.deny_all_hooks_but(*cloner.config.compulsory_hooks_categories):
                cloner.clone(original=c.eid)
                cnx.commit()

            c2 = cnx.entity_from_eid(clone.eid)
            self.assertEqual(u'Babar', c2.reverse_in_circus[0].animals[0].name)


if __name__ == '__main__':
    unittest_main()
