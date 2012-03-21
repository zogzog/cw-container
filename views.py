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

"""cubicweb-container views/forms/actions/components for web ui"""

from cubicweb import schema
from cubicweb.selectors import EClassPredicate
from cubicweb.web import uicfg

from cubes.container import entities

for rtype in ('container_etype', 'container_parent'):
    uicfg.primaryview_section.tag_subject_of(('*', rtype, '*'), 'hidden')
    uicfg.primaryview_section.tag_object_of(('*', rtype, '*'), 'hidden')

    uicfg.autoform_section.tag_subject_of(('*', rtype, '*'), 'main', 'hidden')
    uicfg.autoform_section.tag_object_of(('*', rtype, '*'), 'main', 'hidden')


class is_container(EClassPredicate):
    etypes = set()

    def score_class(self, eclass, req):
        return (eclass.__name__ in self.etypes) * 4

def setup_container_ui(vreg):
    # for all containers, put the <container> rtype in META
    cetypes = entities.container_etypes(vreg)
    is_container.etypes = cetypes
    schema.META_RTYPES.update(vreg['etypes'].etype_class(etype).container_rtype
                              for etype in cetypes)

def registration_callback(vreg):
    # Until cw.after-registry-load events become reliable
    # this must be called in client cubes.
    # setup_container_ui(vreg)
    pass
