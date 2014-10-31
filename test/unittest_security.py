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
            afile = req.create_entity('XFile', data=Binary('foo'))
            ver = new_version(req, projeid)
            tick = new_ticket(req, projeid, ver)
            patch = new_patch(req, tick, afile)
            cnx.commit()

        with self.userlogin('reader') as cnx:
            req = cnx.request()
            projeid = req.execute('Project P').get_entity(0, 0)
            afile = req.create_entity('XFile', data=Binary('foo'))
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


def rulerepr(rule):
    if isinstance(rule, basestring):
        return rule
    rql = rule.rqlst.as_string().split('WHERE ')[1] # cut the WHERE
    rql = ','.join(rql.split(',')[:-2]) # cut the trailing X eid, U eid ...
    return 'EXPR(%s)' % rql

def permsrepr(perms):
    out = {}
    for action in ('read', 'add', 'update', 'delete'):
        out[action] = tuple(rulerepr(rule)
                            for rule in perms.get(action, ()))
    return out

class SecurityTC(CubicWebTC):
    appid = 'data-security'

    def test_rdefs(self):
        project = Container.by_etype('Project')
        self.assertEquals(set([('version_of', 'Version', 'Project'),
                               ('documented_by', 'Project', 'XFile')]),
                           set(rdefrepr(rdef) for rdef in project.rdefs))

        version = Container.by_etype('Version')
        self.assertEquals(set([('done_in_version', 'Ticket', 'Version'),
                               ('documented_by', 'Version', 'XFile'),
                               ('documented_by', 'Ticket', 'XFile')]),
                           set(rdefrepr(rdef) for rdef in version.rdefs))

    def test_border_rdefs_and_permissions(self):
        project = Container.by_etype('Project')
        self.assertEqual(set([('canwrite', 'Project', 'CWUser'),
                              ('canread', 'Project', 'CWUser')]),
                         set(rdefrepr(rdef) for rdef in project.border_rdefs))

        expected = {('canwrite', 'Project', 'CWUser'):
                    {'add': ('managers', 'EXPR(S project P, U canwrite P)'),
                     'delete': ('managers', 'EXPR(S project P, U canwrite P)'),
                     'read': ('managers', 'users'),
                     'update': ()},
                    ('canread', 'Project', 'CWUser'):
                    {'add': ('managers', 'EXPR(S project P, U canwrite P)'),
                     'delete': ('managers', 'EXPR(S project P, U canwrite P)'),
                     'read': ('managers', 'users'),
                     'update': ()}}

        self.assertEqual(expected,
                         {rdefrepr(rdef): permsrepr(rdef.permissions)
                          for rdef in project.border_rdefs})

        version = Container.by_etype('Version')
        self.assertEqual(set([('version_of', 'Version', 'Project'),
                              ('canread', 'Version', 'CWUser'),
                              # NOTE: since XFile is an etype of the Version container
                              # this rdef appears as a border.
                              # It may cause problems when weaving permissions rules
                              # if not properly considered.
                              ('documented_by', 'Project', 'XFile'),
                              ('canwrite', 'Version', 'CWUser')]),
                         set(rdefrepr(rdef) for rdef in version.border_rdefs))

        expected = {('canread', 'Version', 'CWUser'):
                    {'add': ('managers',),
                     'delete': ('managers',),
                     'read': ('managers', 'users', 'guests'),
                     'update': ()},
                    ('canwrite', 'Version', 'CWUser'):
                    {'add': ('managers',),
                     'delete': ('managers',),
                     'read': ('managers', 'users', 'guests'),
                     'update': ()},
                    ('documented_by', 'Project', 'XFile'):
                    {'add': ('managers', 'project_managers'),
                     'delete': ('managers', 'project_managers'),
                     'read': ('managers', 'users'),
                     'update': ()},
                    ('version_of', 'Version', 'Project'):
                    {'add': ('managers', 'EXPR(O project P, U canwrite P)'),
                     'delete': ('managers', 'EXPR(O project P, U canwrite P)'),
                     'read': ('managers', 'users'),
                     'update': ()}}

        self.assertEqual(expected,
                         {rdefrepr(rdef): permsrepr(rdef.permissions)
                          for rdef in version.border_rdefs})

    def test_etypes_permissions(self):
        schema = self.schema
        self.assertEqual({'read': ('managers', 'EXPR((X owned_by U) OR (U canread X))'),
                          'add': ('managers', 'users'),
                          'update': ('managers', 'owners', 'EXPR(U canwrite X)'),
                          'delete': ('managers', 'owners')},
                         permsrepr(schema['Project'].permissions))
        self.assertEqual({'read': ('managers', 'EXPR((X owned_by U) OR (X project C, U canread C))'),
                          'add': ('managers', 'users'),
                          'update': ('managers', 'owners', 'EXPR(X project C, U canwrite C)'),
                          'delete': ('managers', 'owners')},
                         permsrepr(schema['Version'].permissions))
        self.assertEqual({'read': ('managers', 'EXPR((X owned_by U) OR (X version C, U canread C))'),
                          'add': ('managers', 'users'),
                          'update': ('managers', 'owners', 'EXPR(X version C, U canwrite C)'),
                          'delete': ('managers', 'owners')},
                         permsrepr(schema['Ticket'].permissions))
        # NOTE: here, the XFile etype security is clearly wrong for a real world usage
        # we probably would like to combine security rules from all its containers
        # The "collaboration" cube would probably love to have some machinery
        # to automate this.
        self.assertEqual({'read': ('managers', 'EXPR((X owned_by U) OR (X project C, U canread C))'),
                          'add': ('managers', 'users'),
                          'update': ('managers', 'owners', 'EXPR(X project C, U canwrite C)'),
                          'delete': ('managers', 'owners')},
                         permsrepr(schema['XFile'].permissions))

    def test_shared_rtypes_permissions(self):
        ticket_documented_by_rdef = self.schema['documented_by'].rdef('Ticket', 'XFile')
        version_documented_by_rdef = self.schema['documented_by'].rdef('Version', 'XFile')
        project_documented_by_rdef = self.schema['documented_by'].rdef('Project', 'XFile')

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
