from yams.buildobjs import EntityType, RelationDefinition, SubjectRelation, String, Int

# triggers an important monkeypatch on the schema object
from cubes.container import utils

class Diamond(EntityType):
    name = String()
    require_group = SubjectRelation('CWGroup')

class Left(EntityType):
    # defines structure
    top_from_left = SubjectRelation('Diamond', composite='object',
                                    cardinality='1?', inlined=True)
    # outgoing rtype
    watcher = SubjectRelation('CWUser')

class Right(EntityType):
    # defines structure
    top_from_right = SubjectRelation('Diamond', composite='object',
                                     cardinality='1?', inlined=True)
    # in-container rtype
    to_inner_left = SubjectRelation('Left')
    loop_in_place = SubjectRelation('Right')

class IAmAnAttributeCarryingRelation(EntityType):
    to_left = SubjectRelation('Left', composite='object')
    to_right = SubjectRelation('Right', composite='object')
    foo = Int()

class Bottom(EntityType):
    # defines structure
    top_by_left = SubjectRelation('Left', composite='object',
                                  cardinality='??', inlined=True)
    top_by_right = SubjectRelation('Right', composite='object',
                                   cardinality='??', inlined=True)


class Mess(EntityType):
    # security related: must not be cloned/exported, etc.
    local_group = SubjectRelation('CWGroup', composite='subject')

class to_mess(RelationDefinition):
    # relation to an entity also possibly in Diamond
    subject = 'Bottom'
    object = 'Mess'
    composite = 'object'
    cardinality = '??'

def post_build_callback(schema):
    schema.define_container('Diamond', 'diamond')
    schema.define_container('Mess', 'in_mess')


