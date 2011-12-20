# copyright 2011 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr -- mailto:contact@logilab.fr
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 2.1 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program. If not, see <http://www.gnu.org/licenses/>.

"""cubicweb-container entity's classes"""

from logilab.common.decorators import cached, cachedproperty

from cubicweb.entities import AnyEntity
from cubicweb.view import EntityAdapter

from cubes.container.utils import _composite_rschemas, yet_unset

class Container(AnyEntity):
    __abstract__ = True

    # container API
    container_rtype = None
    container_skiprtypes = ()
    container_computedrtypes = ()

@cached
def container_etypes(vreg):
    return set(c.__regid__
               for c, in vreg['etypes'].itervalues()
               if getattr(c, 'container_rtype', False))

class ContainerProtocol(EntityAdapter):
    __regid__ = 'Container'

    @property
    def related_container(self):
        if self.entity.e_schema in container_etypes(self._cw.vreg):
            return self.entity
        try:
            ccwetype = self.entity.container_etype
        except AttributeError:
            return None
        if ccwetype:
            etypes = self._cw.vreg['etypes']
            crtype = etypes.etype_class(ccwetype[0].name).container_rtype
            if hasattr(self.entity, crtype):
                container = getattr(self.entity, crtype)
                if container:
                    return container[0]
        parent = self.parent
        if parent:
            return parent.cw_adapt_to('Container').related_container

    @property
    def parent(self):
        parent = self.entity.container_parent
        return parent[0] if parent else None

class MultiParentProtocol(EntityAdapter):
    __regid__ = 'container.multiple_parents'
    __select__ = yet_unset()

    def possible_parent(self, rtype, eid):
        pass

