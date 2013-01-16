from cubes.container import utils

def unneeded_container_parent_rdefs(schema):
    rdefs = []
    for subj, obj in schema['container_parent'].rdefs:
        if not utils.needs_container_parent(subj):
            rdefs.append((subj, obj))
    return rdefs

for subj, obj in unneeded_container_parent_rdefs(schema):
    drop_relation_definition(subj.type, 'container_parent', obj.type)

