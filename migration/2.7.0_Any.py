from cubes.container import config as cconfig

for etype in cconfig.Container.all_etypes():
    conf = cconfig.Container.by_etype(etype)
    add_relation_definition(etype, conf.crtype, etype)
    add_relation_definition(etype, 'container_etype', 'CWEType')

