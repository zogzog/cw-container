from logilab.common.testlib import unittest_main

from cubicweb import Binary, ValidationError
from cubicweb.devtools.testlib import CubicWebTC

from cubes.container.testutils import userlogin, new_version, new_ticket, new_patch

class SecurityTC(CubicWebTC):

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
