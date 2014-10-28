from yams.buildobjs import EntityType, RelationDefinition, String, SubjectRelation, Bytes
from cubicweb.schema import RRQLExpression, ERQLExpression, PUB_SYSTEM_REL_PERMS

from cubes.container import utils, config
from cubes.container.secutils import PERM, PERMS

class Project(EntityType):
    name = String(required=True, fulltextindexed=True)
    __permissions__ = {
        'read':   ('managers', ERQLExpression('X owned_by U'),
                   ERQLExpression('U canread X')),
        'add':    ('managers', 'users'),
        'update': ('managers', ERQLExpression('U canwrite X')),
        'delete': ('managers', ERQLExpression('U canwrite X'))
    }
    subproject_of = SubjectRelation('Project', composite='object',
                                    inlined=True, cardinality='?*')


PERMS['project-meta-perms'] = {
    'read':   ('managers', 'users', 'guests'),
    'add':    ('managers', RRQLExpression('O owned_by S')),
    'delete': ('managers', RRQLExpression('O owned_by S'))
}

# a standard read-write permission scheme
class canread(RelationDefinition):
    __permissions__ = PERM('project-meta-perms')
    subject = 'CWUser'
    object = 'Project'

class canwrite(RelationDefinition):
    __permissions__ = PERM('project-meta-perms')
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
    done_in_version = SubjectRelation('Version', cardinality='?*', inlined=True)


# ad-hoc rule
PERMS['patch-content'] = {
    'read':   ('managers', 'users'),
    'add':    ('managers', RRQLExpression('S project P, U canwrite P')),
    'delete': ('managers', RRQLExpression('S implements T, NOT T done_in_version V'))
}

@project
class Patch(EntityType):
    name = String(required=True, maxsize=64)
    content = SubjectRelation('XFile', cardinality='1*', inlined=True,
                              __permissions__=PERM('patch-content'))
    implements = SubjectRelation('Ticket', cardinality='1*',
                                 composite='object', inlined=True)


class XFile(EntityType):
    """ does NOT belong to Project """
    data = Bytes()


# let's leave security there and complete the setup with an embedded container

class Folder(EntityType):
    __unique_together__ = [('name', 'parent')]
    name = String(required=True)
    parent = SubjectRelation('Folder', inlined=True,
                             cardinality='?*', composite='object')
    element = SubjectRelation('XFile', composite='subject')


class documents(RelationDefinition):
    subject = 'Folder'
    object = 'Project'
    composite = 'object'


# let's have something to test properly match_rdefs
# i.e. Card has two upward paths and uses 'element'
# and also XFile is a Folder 'element'

class Card(EntityType):
    contents = String()


class element(RelationDefinition):
    subject = 'Folder'
    object = 'Card'
    composite = 'subject'


class requirement(RelationDefinition):
    subject = 'Ticket'
    object = 'Card'
    composite = 'subject'


def post_build_callback(schema):
    project = config.Container('Project', 'project',
                               subcontainers=('Folder', 'Project'))
    project.define_container(schema)

    folder = config.Container('Folder', 'folder_root')
    folder.define_container(schema)

    def inner_rdefs_perms(role_to_container):
        # role_to_container is either 'S' or 'O'
        return {
            'read':   ('managers', 'users', 'guests'),
            'add':    ('managers', RRQLExpression('%s project P, U canwrite P' % role_to_container)),
            'delete': ('managers', RRQLExpression('%s project P, U canwrite P' % role_to_container)),
        }


    project.setup_rdefs_security(inner_rdefs_perms, inner_rdefs_perms)
    folder.setup_rdefs_security(PUB_SYSTEM_REL_PERMS)
