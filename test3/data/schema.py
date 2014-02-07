from yams.buildobjs import EntityType, SubjectRelation, String

from cubes.container import utils


class Circus(EntityType):
    clowns = SubjectRelation('Clown', cardinality='*?', composite='subject')
    cabals = SubjectRelation('ClownCabal', cardinality='*?', composite='subject')


class Clown(EntityType):
    name = String()
    jokes = SubjectRelation('Joke', cardinality='*1', composite='subject')


class ClownCabal(EntityType):
    members = SubjectRelation('Clown', cardinality='*?', composite='subject')


class Joke(EntityType):
    content = String()


def post_build_callback(schema):
    utils.define_container(schema, 'Circus', 'circus')
