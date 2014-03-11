from yams.buildobjs import EntityType, SubjectRelation, String

from config import CIRCUS_CONTAINER, MENAGERIE_CONTAINER


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


class Menagerie(EntityType):
    animals = SubjectRelation('Animal', composite='subject', cardinality='*?')
    in_circus = SubjectRelation('Circus', composite='object', cardinality='?*')


class Animal(EntityType):
    name = String()


def post_build_callback(schema):
    CIRCUS_CONTAINER.define_container(schema)
    MENAGERIE_CONTAINER.define_container(schema)
