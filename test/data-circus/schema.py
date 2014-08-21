from yams.buildobjs import EntityType, SubjectRelation, String

from cubes.container import utils, config


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


class Umbrella(EntityType):
    """ An etype defining Circus as a component """
    has_circus = SubjectRelation('Circus', composite='subject')


def post_build_callback(schema):
    circus = config.Container('Circus', 'circus', subcontainers=('Menagerie',))
    menagerie = config.Container('Menagerie', 'zoo')
    circus.define_container(schema)
    menagerie.define_container(schema)
