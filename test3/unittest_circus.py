from logilab.common.testlib import unittest_main

from cubicweb.devtools.testlib import CubicWebTC

from cubes.container import utils


class CircusTC(CubicWebTC):

    def test_static_structure(self):
        schema = self.vreg.schema
        diamond = self.vreg['etypes'].etype_class('Circus')
        rtypes, etypes = utils.container_static_structure(
            schema, 'Circus', 'circus')
        self.assertSetEqual(set(('Clown', 'ClownCabal', 'Joke')), etypes)
        self.assertSetEqual(set(('clowns', 'cabals', 'jokes', 'members')), rtypes)

    def test_clown_in_cabal_not_in_circus(self):
        req = self.request()
        bozo = req.create_entity('Clown', name=u'Bozo')
        req.create_entity('Joke', content=u'funny', reverse_jokes=bozo)
        req.create_entity('ClownCabal', members=bozo)
        self.commit()


if __name__ == '__main__':
    unittest_main()
