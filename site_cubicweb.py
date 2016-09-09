from logilab.common.decorators import monkeypatch

from yams.reader import SchemaLoader

from cubicweb import schema as cw_schema


cw_schema.META_RTYPES.update(('container_etype', 'container_parent'))


orig_load = SchemaLoader.load


@monkeypatch(SchemaLoader)
def load(*args, **kwargs):
    """Add schema.fs attribute allowing to tell if schema has been loaded from the filesystem"""
    SchemaLoader.schemacls.fs = True
    schema = orig_load(*args, **kwargs)
    SchemaLoader.schemacls.fs = False
    schema.fs = True
    return schema
