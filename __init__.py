# copyright 2013-2014 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of CubicWeb.
#
# CubicWeb is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 2.1 of the License, or (at your option)
# any later version.
#
# CubicWeb is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with CubicWeb.  If not, see <http://www.gnu.org/licenses/>.
"""cubicweb-container application package

provides "generic container" services
"""

import sys
from os.path import join
import logging

from logilab.common.decorators import monkeypatch
from logilab.common.modutils import cleanup_sys_modules

from yams.reader import SchemaLoader, fill_schema

from cubicweb import schema as cw_schema

cw_schema.META_RTYPES.update(('container_etype', 'container_parent'))



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
    sys.modules[SchemaLoader.__module__].context = self
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




LOGGER = logging.getLogger('cubes.container')
cw_schema.META_RTYPES.update(('container_etype', 'container_parent'))
