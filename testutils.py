from contextlib import contextmanager

@contextmanager
def userlogin(self, *args):
    cnx = self.login(*args)
    yield cnx
    self.restore_connection()

def new_version(req, proj, name=u'0.1.0'):
    return req.create_entity('Version', name=name,
                             version_of=proj)

def new_ticket(req, proj, ver):
    return req.create_entity('Ticket', name=u'think about it',
                             description=u'start stuff',
                             concerns=proj, done_in_version=ver)

def new_patch(req, tick, afile):
    return req.create_entity('Patch', name=u'some code',
                             content=afile, implements=tick)
