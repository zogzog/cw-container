from yams.buildobjs import EntityType, RelationDefinition, String, SubjectRelation, Bytes
from cubicweb.schema import RRQLExpression, ERQLExpression

from cubes.container import utils
from cubes.container.secutils import PERM, PERMS, setup_container_rtypes_security
from cubicweb.schema import PUB_SYSTEM_REL_PERMS

# custom ad-hoc rules
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
    documented_by = SubjectRelation('File', cardinality='*?',
                                    __permissions__=PERM('project-documentation'),
                                    composite='subject')


class Version(EntityType):
    __unique_together__ = [('name', 'version_of')]
    name = String(required=True, maxsize=16)
    version_of = SubjectRelation('Project', cardinality='1*',
                                  composite='object', inlined=True)
    documented_by = SubjectRelation('File', cardinality='*?',
                                    composite='subject',
                                    __permissions__=PERM('version-documentation'))


class Ticket(EntityType):
    name = String(required=True, maxsize=64)
    description = String(required=True)
    done_in_version = SubjectRelation('Version', cardinality='?*',
                                      composite='object', inlined=True)
    documented_by = SubjectRelation('File', cardinality='*?',
                                    composite='subject',
                                    __permissions__=PERM('ticket-documentation'))


class File(EntityType):
    """ Belongs to Project, Version and Ticket """
    data = Bytes()


def setup_security(schema):
    # Project container security setup
    def project_rtypes_perms(role_to_container):
        # role_to_container is either 'S' or 'O'
        return PUB_SYSTEM_REL_PERMS

    def near_project_rtype_perms(role_to_container):
        # role_to_container is either 'S' or 'O'
        return PUB_SYSTEM_REL_PERMS


    from cubes.container.entities import Container
    class Project(Container):
        __regid__ = 'Project'
        container_rtype = 'project'
        container_subcontainers = ('Version',)

    setup_container_rtypes_security(schema,
                                    Project,
                                    near_project_rtype_perms,
                                    inner_rtypes_perms=project_rtypes_perms,
                                    border_rtypes_perms=project_rtypes_perms)

    # Version container security setup
    def version_rtypes_perms(role_to_container):
        # role_to_container is either 'S' or 'O'
        return PUB_SYSTEM_REL_PERMS

    def near_version_rtype_perms(role_to_container):
        # role_to_container is either 'S' or 'O'
        return PUB_SYSTEM_REL_PERMS

    class Version(Container):
        __regid__ = 'Version'
        container_rtype = 'version'

    setup_container_rtypes_security(schema,
                                    Version,
                                    near_version_rtype_perms,
                                    inner_rtypes_perms=version_rtypes_perms,
                                    border_rtypes_perms=version_rtypes_perms)

# let's leave security there and complete the setup with an embedded container


def post_build_callback(schema):
    utils.define_container(schema, 'Project', 'project', subcontainers=('Version',))
    utils.define_container(schema, 'Version', 'version')
    setup_security(schema)
