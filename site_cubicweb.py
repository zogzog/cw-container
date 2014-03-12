
from cubicweb.server.sources.native import NativeSQLSource
from logilab.common.decorators import monkeypatch

# clone: fast eid range creation
@monkeypatch(NativeSQLSource)
def _create_eid_sqlite(self, session, count=1, eids=None):
    with self._eid_cnx_lock:
        eids = []
        for _x in xrange(count):
            for sql in self.dbhelper.sqls_increment_sequence('entities_id_seq'):
                cursor = self.doexec(session, sql)
            eids.append(cursor.fetchone()[0])
        if count > 1:
            return eids
        return eids[0]

@monkeypatch(NativeSQLSource)
def create_eid(self, session, count=1):
    with self._eid_cnx_lock:
        return self._create_eid(count)

@monkeypatch(NativeSQLSource)
def _create_eid(self, count, eids=None):
    # internal function doing the eid creation without locking.
    # needed for the recursive handling of disconnections (otherwise we
    # deadlock on self._eid_cnx_lock
    if self._eid_creation_cnx is None:
        self._eid_creation_cnx = self.get_connection()
    cnx = self._eid_creation_cnx
    try:
        eids = eids or []
        cursor = cnx.cursor()
        for _x in xrange(count):
            for sql in self.dbhelper.sqls_increment_sequence('entities_id_seq'):
                cursor.execute(sql)
            eids.append(cursor.fetchone()[0])
    except (self.OperationalError, self.InterfaceError):
        # FIXME: better detection of deconnection pb
        self.warning("trying to reconnect create eid connection")
        self._eid_creation_cnx = None
        return self._create_eid(count, eids)
    except self.DbapiError as exc:
        # We get this one with pyodbc and SQL Server when connection was reset
        if exc.args[0] == '08S01':
            self.warning("trying to reconnect create eid connection")
            self._eid_creation_cnx = None
            return self._create_eid(count, eids)
        else:
            raise
    except Exception:
        cnx.rollback()
        self._eid_creation_cnx = None
        self.exception('create eid failed in an unforeseen way on SQL statement %s', sql)
        raise
    else:
        cnx.commit()
        # one eid vs many
        # we must take a list because the postgres sequence does not
        # ensure a contiguous sequence
        if count > 1:
            return eids
        return eids[0]


try:
    from cubicweb.devtools.testlib import CubicWebTC
except ImportError:
    # devtools may not be installed.
    pass
else:
    # Monkey patch set_cnx as it is a method called after repo initialization.
    orig_set_cnx = CubicWebTC.set_cnx

    @monkeypatch(CubicWebTC, methodname='set_cnx')
    @classmethod
    def set_cnx(cls, cnx):
        orig_set_cnx(cnx)
        patched_create_eid = cls.repo.system_source._create_eid_sqlite
        cls.repo.system_source.create_eid = patched_create_eid
