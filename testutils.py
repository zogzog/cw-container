from contextlib import contextmanager

from cubicweb.__pkginfo__ import numversion
from cubicweb.devtools.testlib import CubicWebTC


@contextmanager
def userlogin(self, *args):
    cnx = self.login(*args)
    yield cnx
    self.restore_connection()

def new_version(req, proj, name=u'0.1.0'):
    return req.create_entity('Version', name=name,
                             version_of=proj)

def new_ticket(req, proj, ver, name=u'think about it', descr=u'start stuff'):
    return req.create_entity('Ticket', name=name,
                             description=descr,
                             concerns=proj, done_in_version=ver)

def new_patch(req, tick, afile, name=u'some code'):
    return req.create_entity('Patch', name=name,
                             content=afile, implements=tick)

def new_card(req, contents=u"Let's start a spec ..."):
    return req.create_entity('Card', contents=contents)


def rdefrepr(rdef):
    """ rdef -> (rtype, subject type, object type) """
    return  (rdef.rtype.type, rdef.subject.type, rdef.object.type)


class ContainerTC(CubicWebTC):

    def setUp(self):
        super(ContainerTC, self).setUp()
        if numversion[:2] < (3, 19):
            # utils monkeypatch had the time to fire
            patched_create_eid = self.session.repo.system_source._create_eid_sqlite
            self.session.repo.system_source.create_eid = patched_create_eid
