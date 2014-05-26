
for rschema in schema.relations():
  for etype in rschema.subjects() + rschema.objects():
    if schema[etype].has_relation('container_etype', 'subject'):
      sync_schema_props_perms(rschema.type, syncprops=False, commit=False)
      break
commit()
