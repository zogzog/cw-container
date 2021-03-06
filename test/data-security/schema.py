from yams.buildobjs import EntityType, String, SubjectRelation, Bytes
from cubicweb.schema import RRQLExpression, ERQLExpression, PUB_SYSTEM_REL_PERMS

from cubes.container import config
from cubes.container.secutils import PERM, PERMS

# custom ad-hoc rules
PERMS['project'] = {
    'read':   ('managers', ERQLExpression('(X owned_by U) OR (U canread X)')),
    'add':    ('managers', 'users'),
    'delete': ('managers', 'owners'),
    'update': ('managers', 'owners', ERQLExpression('U canwrite X')),
}

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
    __permissions__ = PERM('project')
    name = String(required=True)
    documented_by = SubjectRelation('XFile', cardinality='*?',
                                    __permissions__=PERM('project-documentation'),
                                    composite='subject')
    canread = SubjectRelation('CWUser')
    canwrite = SubjectRelation('CWUser')


class Version(EntityType):
    __unique_together__ = [('name', 'version_of')]
    name = String(required=True, maxsize=16)
    version_of = SubjectRelation('Project', cardinality='1*',
                                  composite='object', inlined=True)
    documented_by = SubjectRelation('XFile', cardinality='*?',
                                    composite='subject',
                                    __permissions__=PERM('version-documentation'))
    canread = SubjectRelation('CWUser')
    canwrite = SubjectRelation('CWUser')


class Ticket(EntityType):
    name = String(required=True, maxsize=64)
    description = String(required=True)
    done_in_version = SubjectRelation('Version', cardinality='?*',
                                      composite='object', inlined=True)
    documented_by = SubjectRelation('XFile', cardinality='*?',
                                    composite='subject',
                                    __permissions__=PERM('ticket-documentation'))


class XFile(EntityType):
    """ Belongs to Project, Version and Ticket """
    data = Bytes()


def post_build_callback(schema):
    config._CONTAINER_ETYPE_MAP.clear()

    project = config.Container('Project', 'project', subcontainers=('Version',))
    project.define_container(schema)
    version = config.Container('Version', 'version')
    version.define_container(schema)

    def project_rtypes_perms(role_to_container):
        # role_to_container is either 'S' or 'O'
        return {
            'read': ('managers', 'users'),
            'add': ('managers',
                    RRQLExpression('%s project P, U canwrite P' % role_to_container)),
            'delete': ('managers',
                       RRQLExpression('%s project P, U canwrite P' % role_to_container))
        }

    project.setup_rdefs_security(schema, project_rtypes_perms, project_rtypes_perms)

    # version container & security
    version.setup_rdefs_security(schema, PUB_SYSTEM_REL_PERMS, PUB_SYSTEM_REL_PERMS)

    for conf in (version, project):
        conf.setup_etypes_security(schema, {
            'read':   ('managers',
                       ERQLExpression('(X owned_by U) OR (X %s C, U canread C)' % conf.crtype)),
            'add':    ('managers', 'users'),
            'delete': ('managers', 'owners'),
            'update': ('managers', 'owners',
                       ERQLExpression('X %s C, U canwrite C' % conf.crtype)),
        })
