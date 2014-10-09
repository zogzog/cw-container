from itertools import chain

from cubicweb.server import ON_COMMIT_ADD_RELATIONS

from config import PROJECT_CONTAINER

def registration_callback(vreg):
    if not PROJECT_CONTAINER.register_container_hooks(vreg):
        return
    schema = vreg.schema
    # security setup: need to check relations using relation to container in
    # their perms on commit
    for rschema, _ in chain(PROJECT_CONTAINER.structural_relations_to_container(schema),
                            PROJECT_CONTAINER.structural_relations_to_parent(schema),
                            PROJECT_CONTAINER.border_relations(schema)):
        ON_COMMIT_ADD_RELATIONS.add(rschema.type)
    for rschema in PROJECT_CONTAINER.inner_relations(schema):
        ON_COMMIT_ADD_RELATIONS.add(rschema.type)
