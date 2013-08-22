from contextlib import contextmanager

from logilab.common.testlib import unittest_main

from cubicweb import Binary, ValidationError
from cubicweb.devtools.testlib import CubicWebTC


class SecurityTC(CubicWebTC):

    @contextmanager
    def userlogin(self, *args):
        cnx = self.login(*args)
        yield cnx
        self.restore_connection()

    def setup_database(self):
        req = self.request()
        proj = req.create_entity('Project', name=u'Babar')
        user = self.create_user(req, login=u'user', groups=('users',))
        reader = self.create_user(req, login=u'reader', groups=('users',))
        writer = self.create_user(req, login=u'writer', groups=('users',))
        reader.set_relations(canread=proj)
        writer.set_relations(canread=proj, canwrite=proj)

    def test_base(self):
        with self.userlogin('writer') as cnx:
            req = cnx.request()
            projeid = req.execute('Project P').get_entity(0, 0)
            afile = req.create_entity('File', data=Binary('foo'))
            ver = self._new_version(req, projeid)
            tick = self._new_ticket(req, projeid, ver)
            patch = self._new_patch(req, tick, afile)
            cnx.commit()

        with self.userlogin('reader') as cnx:
            req = cnx.request()
            projeid = req.execute('Project P').get_entity(0, 0)
            afile = req.create_entity('File', data=Binary('foo'))
            ver = self._new_version(req, projeid, u'0.2.0')
            tick = self._new_ticket(req, projeid, ver)
            patch = self._new_patch(req, tick, afile)
            self.assertRaises(cnx.commit)
            cnx.rollback()
            req = cnx.request()
            ver = self._new_version(req, projeid, u'0.3.0')
            self.assertRaises(cnx.commit)

        with self.userlogin('user') as cnx:
            req = cnx.request()
            self.assertEqual(0, req.execute('Project P').rowcount)
            self.assertEqual(0, req.execute('Any P,E WHERE E project P').rowcount)

    def _new_version(self, req, proj, name=u'0.1.0'):
        return req.create_entity('Version', name=name,
                                 version_of=proj)

    def _new_ticket(self, req, proj, ver):
        return req.create_entity('Ticket', name=u'think about it',
                                 description=u'start stuff',
                                 concerns=proj, done_in_version=ver)

    def _new_patch(self, req, tick, afile):
        return req.create_entity('Patch', name=u'some code',
                                 content=afile, implements=tick)

if __name__ == '__main__':
    unittest_main()
