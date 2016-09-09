from yams.buildobjs import EntityType, RelationDefinition, SubjectRelation, String, Int
from cubicweb.schema import WorkflowableEntityType

from cubes.container import utils, config

class Diamond(EntityType):
    name = String()
    require_group = SubjectRelation('CWGroup')
    has_near_top = SubjectRelation('NearTop', composite='subject',
                                   cardinality='*?')

class NearTop(EntityType):
    pass

class Left(EntityType):
    # defines structure
    top_from_left = SubjectRelation('Diamond', composite='object',
                                    cardinality='?*', inlined=True)
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


class is_clone_of(RelationDefinition):
    subject = 'Diamond'
    object = 'Diamond'
    cardinality = '?*'


class Mess(WorkflowableEntityType):
    # security related: must not be cloned/exported, etc.
    local_group = SubjectRelation('CWGroup', composite='subject')

class to_mess(RelationDefinition):
    # relation to an entity also possibly in Diamond
    subject = 'Bottom'
    object = 'Mess'
    composite = 'object'
    cardinality = '??'


# Assert skipetypes
class EtypeNotInContainers(EntityType):
    pass

class composite_but_not_in_diamond(RelationDefinition):
    subject = 'EtypeNotInContainers'
    object = 'Left'
    composite = 'object'


class linked_to_mess(RelationDefinition):
    subject = 'EtypeNotInContainers'
    object = 'Mess'


def post_build_callback(schema):
    config._CONTAINER_ETYPE_MAP.clear()

    diamond = config.Container('Diamond', 'diamond',
                               skipetypes=('EtypeNotInContainers',),
                               clone_rtype_role=('is_clone_of', 'subject'))
    mess = config.Container('Mess', 'in_mess',
                            skiprtypes = ('local_group', 'wf_info_for'))
    diamond.define_container(schema)
    mess.define_container(schema)


