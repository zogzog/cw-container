"""cubicweb-container application package

provides "generic container" services
"""

import sys
from os.path import join

from logilab.common.decorators import monkeypatch
from logilab.common.modutils import cleanup_sys_modules

from yams.reader import SchemaLoader, fill_schema

from cubicweb import schema

schema.META_RTYPES.update(('container_etype', 'container_parent'))



# Add schema.fs til yams gets it.

@monkeypatch(SchemaLoader)
def load(self, directories, name=None,
         register_base_types=True, construction_mode='strict',
         remove_unused_rtypes=True):
    """return a schema from the schema definition read from <directory>
    """
    self.defined = {}
    self.loaded_files = []
    self.post_build_callbacks = []
    sys.modules[__name__].context = self
    # ensure we don't have an iterator
    directories = tuple(directories)
    try:
        self._load_definition_files(directories)
        schema = self.schemacls(name or 'NoName', construction_mode=construction_mode)
        schema.fs = True
        try:
            fill_schema(schema, self.defined, register_base_types,
                        remove_unused_rtypes=remove_unused_rtypes,
                        post_build_callbacks=self.post_build_callbacks)
        except Exception, ex:
            if not hasattr(ex, 'schema_files'):
                ex.schema_files = self.loaded_files
            raise ex, None, sys.exc_info()[-1]
    finally:
        # cleanup sys.modules from schema modules
        # ensure we're only cleaning schema [sub]modules
        directories = [(not directory.endswith(self.main_schema_directory)
                        and join(directory, self.main_schema_directory)
                        or directory)
                       for directory in directories]
        cleanup_sys_modules(directories)
    schema.loaded_files = self.loaded_files
    return schema
