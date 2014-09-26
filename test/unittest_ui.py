from collections import defaultdict

from cubicweb.__pkginfo__ import numversion
from cubicweb.web.views import uicfg

from cubes.container.testutils import ContainerTC
from cubes.container import config

afs = uicfg.autoform_section
pvs = uicfg.primaryview_section

def tree():
    return defaultdict(tree)

notcw319 = numversion[:2] < (3, 19)

class UITC(ContainerTC):
    appid = 'data-tracker'

    def test_uicfg(self):
        for cetype in config.Container.all_etypes():
            conf = config.Container.by_etype(cetype)
            autoformexpected = set(['main_hidden', 'muledit_hidden', 'inlined_hidden'])
            pvexpected = 'hidden'
            for etype in conf.etypes:
                self.assertEqual(autoformexpected,
                                 afs.get(etype, conf.crtype, conf.cetype, 'subject'))
                self.assertEqual(autoformexpected,
                                 afs.get(etype, conf.crtype, conf.cetype, 'object'))
                self.assertEqual(pvexpected,
                                 pvs.get(etype, conf.crtype, '*', 'subject'))
                self.assertEqual(pvexpected,
                                 pvs.get('*', conf.crtype, etype, 'object'))

        p = self.session.create_entity('Project', name=u'Babar')
        d = tree()
        d['main']['attributes']['add'] = [('name', ['String'], 'subject')]
        d['main']['attributes']['update'] = [('name', ['String'], 'subject')]
        d['main']['metadata']['update'] = [('created_by', ['CWUser'], 'subject'),
                                           ('creation_date', ['Datetime'], 'subject'),
                                           ('cw_source', ['CWSource'], 'subject'),
                                           ('cwuri', ['String'], 'subject'),
                                           ('modification_date', ['Datetime'], 'subject'),
                                           ('owned_by', ['CWUser'], 'subject')]
        d['main']['hidden']['update'] = [('concerns', ['Ticket'], 'object'),
                                         ('container_etype', ['CWEType'], 'subject'),
                                         ('container_parent', ['Folder'], 'object'),
                                         ('project', ['Card', 'Folder', 'Patch','Project',
                                                      'Ticket', 'Version'], 'object'),
                                         ('project', ['Project'], 'subject'),
                                         ('version_of', ['Version'], 'object')]
        d['main']['relations']['add'] = [('canread', ['CWUser'], 'object'),
                                         ('canwrite', ['CWUser'], 'object'),
                                         ('documents', ['Folder'], 'object'),
                                         ('subproject_of', ['Project'], 'object'),
                                         ('subproject_of', ['Project'], 'subject')]

        d['muledit']['attributes']['add'] = [('eid', ['Int'], 'subject'),
                                             ('name', ['String'], 'subject')]
        d['muledit']['attributes']['update'] = [('name', ['String'], 'subject')]
        d['muledit']['metadata']['update'] = []
        d['muledit']['hidden']['update'] = [('canread', ['CWUser'], 'object'),
                                            ('canwrite', ['CWUser'], 'object'),
                                            ('concerns', ['Ticket'], 'object'),
                                            ('container_etype', ['CWEType'], 'subject'),
                                            ('container_parent', ['Folder'], 'object'),
                                            ('created_by', ['CWUser'], 'subject'),
                                            ('creation_date', ['Datetime'], 'subject'),
                                            ('cw_source', ['CWSource'], 'subject'),
                                            ('cwuri', ['String'], 'subject'),
                                            ('documents', ['Folder'], 'object'),
                                            ('modification_date', ['Datetime'], 'subject'),
                                            ('owned_by', ['CWUser'], 'subject'),
                                            ('project',
                                             ['Card', 'Folder', 'Patch', 'Project', 'Ticket', 'Version'],
                                             'object'),
                                            ('project', ['Project'], 'subject'),
                                            ('subproject_of', ['Project'], 'object'),
                                            ('subproject_of', ['Project'], 'subject'),
                                            ('version_of', ['Version'], 'object')]
        d['muledit']['relations']['add'] = []

        d['inlined']['attributes']['add'] = [('name', ['String'], 'subject')]
        d['inlined']['attributes']['update'] = [('name', ['String'], 'subject')]
        d['inlined']['metadata']['update'] = []
        d['inlined']['hidden']['update'] = [('concerns', ['Ticket'], 'object'),
                                            ('container_etype', ['CWEType'], 'subject'),
                                            ('container_parent', ['Folder'], 'object'),
                                            ('created_by', ['CWUser'], 'subject'),
                                            ('creation_date', ['Datetime'], 'subject'),
                                            ('cw_source', ['CWSource'], 'subject'),
                                            ('cwuri', ['String'], 'subject'),
                                            ('modification_date', ['Datetime'], 'subject'),
                                            ('owned_by', ['CWUser'], 'subject'),
                                            ('project',
                                             ['Card', 'Folder', 'Patch', 'Project', 'Ticket', 'Version'],
                                             'object'),
                                            ('project', ['Project'], 'subject'),
                                            ('version_of', ['Version'], 'object')]
        d['inlined']['relations']['add'] = [('canread', ['CWUser'], 'object'),
                                            ('canwrite', ['CWUser'], 'object'),
                                            ('documents', ['Folder'], 'object'),
                                            ('subproject_of', ['Project'], 'object'),
                                            ('subproject_of', ['Project'], 'subject')]

        if notcw319:
            skipadd = ('attributes', 'metadata', 'hidden')
        else:
            skipadd = ('metadata', 'hidden')
        for formtype in ('main', 'muledit', 'inlined'):
            for section in ('attributes', 'metadata', 'hidden', 'relations'):
                for action in ('add', 'update'):
                    if action == 'add' and section in skipadd:
                        continue # unsupported
                    if action == 'update' and section == 'relations':
                        continue # unsupported
                    entry = afs.relations_by_section(p, formtype, section, action)
                    got = sorted([(rschema.type, sorted([e.type for e in teschemas]), role)
                                  for rschema, teschemas, role in entry])

                    self.assertEqual(d[formtype][section][action], got), got
