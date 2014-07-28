from logilab.common.testlib import unittest_main

from cubicweb import Binary, Unauthorized
from cubicweb.devtools.testlib import CubicWebTC

from cubes.container.testutils import (userlogin, new_version, new_ticket,
                                       new_patch, rdefrepr)
from cubes.container.config import Container

class BasicSecurityTC(CubicWebTC):
    appid = 'data-tracker'
    userlogin = userlogin

    def setup_database(self):
        req = self.request()
        proj = req.create_entity('Project', name=u'Babar')
        user = self.create_user(req, login=u'user', groups=('users',))
        reader = self.create_user(req, login=u'reader', groups=('users',))
        writer = self.create_user(req, login=u'writer', groups=('users',))
        reader.cw_set(canread=proj)
        writer.cw_set(canread=proj, canwrite=proj)

    def test_base(self):
        with self.userlogin('writer') as cnx:
            req = cnx.request()
            projeid = req.execute('Project P').get_entity(0, 0)
            afile = req.create_entity('File', data=Binary('foo'))
            ver = new_version(req, projeid)
            tick = new_ticket(req, projeid, ver)
            patch = new_patch(req, tick, afile)
            cnx.commit()

        with self.userlogin('reader') as cnx:
            req = cnx.request()
            projeid = req.execute('Project P').get_entity(0, 0)
            afile = req.create_entity('File', data=Binary('foo'))
            ver = new_version(req, projeid, u'0.2.0')
            tick = new_ticket(req, projeid, ver)
            patch = new_patch(req, tick, afile)
            with self.assertRaises(Unauthorized):
                cnx.commit()
            cnx.rollback()
            req = cnx.request()
            ver = new_version(req, projeid, u'0.3.0')
            with self.assertRaises(Unauthorized):
                cnx.commit()

        with self.userlogin('user') as cnx:
            req = cnx.request()
            self.assertEqual(0, req.execute('Project P').rowcount)
            self.assertEqual(0, req.execute('Any P,E WHERE E project P').rowcount)


class SecurityTC(CubicWebTC):
    appid = 'data-security'

    def test_rdefs(self):
        project = Container.by_etype('Project')
        self.assertEquals(set([('version_of', 'Version', 'Project'),
                               ('documented_by', 'Project', 'File')]),
                           set(rdefrepr(rdef) for rdef in project.rdefs))

        version = Container.by_etype('Version')
        self.assertEquals(set([('done_in_version', 'Ticket', 'Version'),
                               ('documented_by', 'Version', 'File'),
                               ('documented_by', 'Ticket', 'File')]),
                           set(rdefrepr(rdef) for rdef in version.rdefs))

    def test_shared_rtypes_permissions(self):
        ticket_documented_by_rdef = self.schema['documented_by'].rdef('Ticket', 'File')
        version_documented_by_rdef = self.schema['documented_by'].rdef('Version', 'File')
        project_documented_by_rdef = self.schema['documented_by'].rdef('Project', 'File')

        self.assertEqual(ticket_documented_by_rdef.permissions['add'][1],
                         'ticket_managers')
        self.assertEqual(version_documented_by_rdef.permissions['add'][1],
                         'version_managers')
        self.assertEqual(project_documented_by_rdef.permissions['add'][1],
                         'project_managers')

        self.assertEqual(ticket_documented_by_rdef.permissions['delete'][1],
                         'ticket_managers')
        self.assertEqual(version_documented_by_rdef.permissions['delete'][1],
                         'version_managers')
        self.assertEqual(project_documented_by_rdef.permissions['delete'][1],
                         'project_managers')



if __name__ == '__main__':
    unittest_main()
