from itertools import chain

from yams.buildobjs import EntityType, RelationDefinition, SubjectRelation, \
    String, Bytes
from cubicweb.schema import RRQLExpression, ERQLExpression

from config import PROJECT_CONTAINER


class Project(EntityType):
    name = String(required=True)
    __permissions__ = {
        'read':   ('managers', ERQLExpression('U canread X')),
        'add':    ('managers', 'users'),
        'update': ('managers', ERQLExpression('U canwrite X')),
        'delete': ('managers', ERQLExpression('U canwrite X'))
    }
    subproject_of = SubjectRelation('Project', composite='object',
                                    inlined=True, cardinality='?*')


# a standard read-write permission scheme
class canread(RelationDefinition):
    subject = 'CWUser'
    object = 'Project'

class canwrite(RelationDefinition):
    subject = 'CWUser'
    object = 'Project'


class Version(EntityType):
    __unique_together__ = [('name', 'version_of')]
    name = String(required=True, maxsize=16)
    version_of = SubjectRelation('Project', cardinality='1*',
                                  composite='object', inlined=True)


class Ticket(EntityType):
    name = String(required=True, maxsize=64)
    description = String(required=True)
    concerns = SubjectRelation('Project', cardinality='1*',
                               composite='object', inlined=True)
    done_in_version = SubjectRelation('Version', cardinality='?*', inlined=True)


class Patch(EntityType):
    name = String(required=True, maxsize=64)
    content = SubjectRelation('XFile', cardinality='1*', inlined=True,
                              __permissions__={
            'read':   ('managers', 'users'),
            'add':    ('managers', RRQLExpression('S project P, U canwrite P')),
            'delete': ('managers', RRQLExpression('S implements T, NOT T done_in_version V'))
            })
    implements = SubjectRelation('Ticket', cardinality='1*',
                                 composite='object', inlined=True)


class XFile(EntityType):
    """ does NOT belong to Project """
    data = Bytes()


def post_build_callback(schema):
    PROJECT_CONTAINER.define_container(schema)
    # setup security
    for rschema, role in PROJECT_CONTAINER.structural_relations_to_container(schema):
        var = role[0].upper()
        for rdef in rschema.rdefs.itervalues():
            rdef.permissions = {
            'read':   ('managers', 'users', 'guests'),
            'add':    ('managers', RRQLExpression('U canwrite %s' % var)),
            'delete': ('managers', RRQLExpression('U canwrite %s' % var)),
            }
    for rschema, role in chain(PROJECT_CONTAINER.structural_relations_to_parent(schema),
                               PROJECT_CONTAINER.border_relations(schema)):
        var = role[0].upper()
        for rdef in rschema.rdefs.itervalues():
            rdef.permissions = {
            'read':   ('managers', 'users', 'guests'),
            'add':    ('managers', RRQLExpression('%s project P, U canwrite P' % var)),
            'delete': ('managers', RRQLExpression('%s project P, U canwrite P' % var)),
            }
    for rschema in PROJECT_CONTAINER.inner_relations(schema):
        for rdef in rschema.rdefs.itervalues():
            rdef.permissions = {
            'read':   ('managers', 'users', 'guests'),
            'add':    ('managers', RRQLExpression('S project P, U canwrite P')),
            'delete': ('managers', RRQLExpression('S project P, U canwrite P')),
            }
