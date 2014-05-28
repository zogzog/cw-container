from contextlib import contextmanager

from cubicweb.schema import (META_RTYPES, WORKFLOW_DEF_RTYPES, SYSTEM_RTYPES,
                             SCHEMA_TYPES, WORKFLOW_TYPES, INTERNAL_TYPES)
from cubes.container import CONTAINERS, ContainerConfiguration


class ContainerMixinTC(object):
    """Test mixin for cubes using container, to avoid registration clashes"""

    @classmethod
    def tearDownClass(cls):
        CONTAINERS.clear()
        super(ContainerMixinTC, cls).tearDownClass()

    @staticmethod
    def replace_config(etype, *args, **kwargs):
        """Replace an already registered container configuration"""
        del CONTAINERS[etype]
        return ContainerConfiguration(etype, *args, **kwargs)


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


def rtypes_etypes_not_in_container(schema, container_config):
    """Return the sets of entity types and relations types not in the
    container."""
    # Entity/relation types from the schema.
    setypes = set(str(e) for e in schema.entities() if not e.final).difference(
        SCHEMA_TYPES, WORKFLOW_TYPES, INTERNAL_TYPES)
    srtypes = set(str(r) for r in schema.relations() if not r.final).difference(
        SCHEMA_TYPES, META_RTYPES, WORKFLOW_DEF_RTYPES, SYSTEM_RTYPES,
        # The following rtypes are not declared (yet) in any of the above
        # global variables (see http://www.cubicweb.org/ticket/3486114).
        ('cw_schema', 'cw_import_of', 'cw_for_source', 'cw_host_config_of',
         'by_transition'))
    # Entity/relation types belonging to the container (incl. non structural
    # rtypes).
    rtypes, etypes = container_config.structure(schema)
    rtypes = rtypes.union(container_config.inner_relations(schema))
    return (frozenset(srtypes.difference(rtypes)),
            frozenset(setypes.difference(etypes)))
