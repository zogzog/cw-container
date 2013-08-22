from yams.buildobjs import EntityType, RelationDefinition, String, SubjectRelation, Bytes
from cubicweb.schema import RRQLExpression, ERQLExpression

from cubes.container import utils
from cubes.container.secutils import PERM, PERMS, setup_container_rtypes_security

class Project(EntityType):
    name = String(required=True)
    __permissions__ = {
        'read':   ('managers', ERQLExpression('U canread X')),
        'add':    ('managers', 'users'),
        'update': ('managers', ERQLExpression('U canwrite X')),
        'delete': ('managers', ERQLExpression('U canwrite X'))
    }

# a standard read-write permission scheme
class canread(RelationDefinition):
    subject = 'CWUser'
    object = 'Project'

class canwrite(RelationDefinition):
    subject = 'CWUser'
    object = 'Project'


def project(etypeclass):
    """ decorator for the in-project entity types
    Sets the permissions
    """
    etypeclass.__permissions__ = {
        'read':   ('managers', ERQLExpression('U canread P, X project P')),
        'add':    ('managers', 'users'), # can't really do it there
        'update': ('managers', ERQLExpression('U canwrite P, X project P')),
        'delete': ('managers', ERQLExpression('U canwrite P, X project P'))
    }
    return etypeclass


@project
class Version(EntityType):
    __unique_together__ = [('name', 'version_of')]
    name = String(required=True, maxsize=16)
    version_of = SubjectRelation('Project', cardinality='1*',
                                  composite='object', inlined=True)


@project
class Ticket(EntityType):
    name = String(required=True, maxsize=64)
    description = String(required=True)
    concerns = SubjectRelation('Project', cardinality='1*',
                               composite='object', inlined=True)
    done_in_version = SubjectRelation('Version', cardinality='?*')


# ad-hoc rule
PERMS['patch-content'] = {
    'read':   ('managers', 'users'),
    'add':    ('managers', RRQLExpression('S project P, U canwrite P')),
    'delete': ('managers', RRQLExpression('S implements T, NOT T done_in_version V'))
}

@project
class Patch(EntityType):
    name = String(required=True, maxsize=64)
    content = SubjectRelation('File', cardinality='1*', inlined=True,
                              __permissions__=PERM('patch-content'))
    implements = SubjectRelation('Ticket', cardinality='1*',
                                 composite='object', inlined=True)


class File(EntityType):
    data = Bytes()

def setup_security(schema):
    def container_rtypes_perms(role_to_container):
        # role_to_container is either 'S' or 'O'
        return {
            'read':   ('managers', 'users', 'guests'),
            'add':    ('managers', RRQLExpression('%s project P, U canwrite P' % role_to_container)),
            'delete': ('managers', RRQLExpression('%s project P, U canwrite P' % role_to_container)),
        }
    def near_container_rtype_perms(role_to_container):
        # role_to_container is either 'S' or 'O'
        return {
            'read':   ('managers', 'users', 'guests'),
            'add':    ('managers', RRQLExpression('U canwrite %s' % role_to_container)),
            'delete': ('managers', RRQLExpression('U canwrite %s' % role_to_container)),
        }

    # from cubes.tracker.entities import Project
    # We need to cheat a bit here because this does not really exist as such
    from cubes.container.entities import Container
    class Project(Container):
        __regid__ = 'Project'
        container_rtype = 'project'

    setup_container_rtypes_security(schema,
                                    Project,
                                    near_container_rtype_perms,
                                    inner_rtypes_perms=container_rtypes_perms,
                                    border_rtypes_perms=container_rtypes_perms)

def post_build_callback(schema):
    utils.define_container(schema, 'Project', 'project')
    setup_security(schema)
