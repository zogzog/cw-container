# -*- coding: utf-8 -*-
from logilab.common.testlib import unittest_main

from cubicweb.devtools.testlib import CubicWebTC


class SecurityTC(CubicWebTC):
    appid = 'data-forge3'

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

    def test_selection_ambiguity(self):
        """Show that a selection ambiguity is raised when attaching XFile
        objects via the documented_by relation to both Project and Version
        containers.
        """
        def process_exception_message(exc):
            """Extract exception kind and extra relevant arguments from
            CubicWeb-specific select ambiguity exception message.
            """
            message = exc.exception.message
            kind, args = message.split(':')[:2]
            args = [arg.strip('<class \'cubes.container.').strip('\'>') for
                    arg in args.strip(' []\n(args').split(',')]
            return tuple([kind] + args)

        req = self.request()
        project = req.create_entity('Project', name=u'Babar')
        version = req.create_entity('Version', name=u'Celeste', version_of=project)
        ticket = req.create_entity('Ticket', name=u'TicketCeleste',
                                   description=u'Ticket de Céleste',
                                   done_in_version=version)
        with self.assertRaises(Exception) as ex:
            proj_file= req.create_entity('XFile', reverse_documented_by=project)
            version_file = req.create_entity('XFile', reverse_documented_by=version)

        # Check that the exception raised is indeed a selection ambiguity
        ex_kind_and_args = process_exception_message(ex)
        self.assertEqual('select ambiguity', ex_kind_and_args[0])
        self.assertEqual(frozenset(['ProjectSetContainerRelation',
                                    'VersionSetContainerRelation']),
                         frozenset(ex_kind_and_args[1:]))


if __name__ == '__main__':
    unittest_main()
