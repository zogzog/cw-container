container_configs = set()
for etype in schema.entities():
    etypecls = session.vreg['etypes'].etype_class(etype.type)
    if hasattr(etypecls, 'container_config'):
        cfg = etypecls.container_config
        sync_schema_props_perms(cfg.rtype, syncprops=False, commit=False)
commit()
