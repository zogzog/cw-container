import types
from itertools import chain

from yams.buildobjs import EntityType, RelationDefinition, String, SubjectRelation, Bytes
from cubicweb.schema import RRQLExpression, ERQLExpression, PUB_SYSTEM_REL_PERMS


from config import PROJECT_CONTAINER, VERSION_CONTAINER

# custom ad-hoc rules
PERMS = {}
PERMS['project-documentation'] = {
    'read':   ('managers', 'users'),
    'add':    ('managers', 'project_managers'),
    'delete': ('managers', 'project_managers')
}

PERMS['version-documentation'] = {
    'read':   ('managers', 'users'),
    'add':    ('managers', 'version_managers'),
    'delete': ('managers', 'version_managers')
}

PERMS['ticket-documentation'] = {
    'read':   ('managers', 'users'),
    'add':    ('managers', 'ticket_managers'),
    'delete': ('managers', 'ticket_managers')
}

class Project(EntityType):
    name = String(required=True)
    documented_by = SubjectRelation('XFile', cardinality='*?',
                                    __permissions__=PERMS['project-documentation'],
                                    composite='subject')


class Version(EntityType):
    __unique_together__ = [('name', 'version_of')]
    name = String(required=True, maxsize=16)
    version_of = SubjectRelation('Project', cardinality='1*',
                                  composite='object', inlined=True)
    documented_by = SubjectRelation('XFile', cardinality='*?',
                                    composite='subject',
                                    __permissions__=PERMS['version-documentation'])


class Ticket(EntityType):
    name = String(required=True, maxsize=64)
    description = String(required=True)
    done_in_version = SubjectRelation('Version', cardinality='?*',
                                      composite='object', inlined=True)
    documented_by = SubjectRelation('XFile', cardinality='*?',
                                    composite='subject',
                                    __permissions__=PERMS['ticket-documentation'])


class XFile(EntityType):
    """ Belongs to Project, Version and Ticket """
    data = Bytes()


def setup_security(container, schema):
    for rschema, role in container.structural_relations_to_container(schema):
        var = role[0].upper()
        for rdef in rschema.rdefs.itervalues():
            if rdef.rtype != 'documented_by':
                rdef.permissions = PUB_SYSTEM_REL_PERMS
    for rschema, role in chain(container.structural_relations_to_parent(schema),
                               container.border_relations(schema)):
        var = role[0].upper()
        for rdef in rschema.rdefs.itervalues():
            if rdef.rtype != 'documented_by':
                rdef.permissions = PUB_SYSTEM_REL_PERMS
    for rschema in container.inner_relations(schema):
        for rdef in rschema.rdefs.itervalues():
            rdef.permissions = PUB_SYSTEM_REL_PERMS

PROJECT_CONTAINER.setup_security = types.MethodType(setup_security, PROJECT_CONTAINER)
VERSION_CONTAINER.setup_security = types.MethodType(setup_security, VERSION_CONTAINER)


def post_build_callback(schema):
    PROJECT_CONTAINER.define_container(schema)
    PROJECT_CONTAINER.setup_security(schema)
    VERSION_CONTAINER.define_container(schema)
    VERSION_CONTAINER.setup_security(schema)
