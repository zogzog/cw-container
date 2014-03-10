from logilab.common.testlib import unittest_main

from cubicweb import Binary, ValidationError, Unauthorized
from cubicweb.devtools.testlib import CubicWebTC

from cubes.container.testutils import userlogin, new_version, new_ticket, new_patch

class SecurityTC(CubicWebTC):
    appid = 'data-forge'

    def setup_database(self):
        req = self.request()
        proj = req.create_entity('Project', name=u'Babar')
        user = self.create_user(req, login=u'user', groups=('users',))
        reader = self.create_user(req, login=u'reader', groups=('users',))
        writer = self.create_user(req, login=u'writer', groups=('users',))
        reader.cw_set(canread=proj)
        writer.cw_set(canread=proj, canwrite=proj)

    def test_base(self):
        with self.login('writer') as cnx:
            req = self.request()
            projeid = req.execute('Project P').get_entity(0, 0)
            afile = req.create_entity('File', data=Binary('foo'))
            ver = new_version(req, projeid)
            tick = new_ticket(req, projeid, ver)
            patch = new_patch(req, tick, afile)
            cnx.commit()

        with self.login('reader') as cnx:
            req = self.request()
            projeid = req.execute('Project P').get_entity(0, 0)
            afile = req.create_entity('File', data=Binary('foo'))
            ver = new_version(req, projeid, u'0.2.0')
            tick = new_ticket(req, projeid, ver)
            patch = new_patch(req, tick, afile)
            with self.assertRaises(Unauthorized):
                cnx.commit()
            cnx.rollback()
            req = self.request()
            ver = new_version(req, projeid, u'0.3.0')
            with self.assertRaises(Unauthorized):
                cnx.commit()

        with self.login('user') as cnx:
            req = self.request()
            self.assertEqual(0, req.execute('Project P').rowcount)
            self.assertEqual(0, req.execute('Any P,E WHERE E project P').rowcount)


if __name__ == '__main__':
    unittest_main()
