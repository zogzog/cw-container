from cubes.container import config

for etype in config.Container.all_etypes():
    conf = config.by_etype(etype)
    add_relation_definition(etype, conf.crtype, etype)
