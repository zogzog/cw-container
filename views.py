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

from cubicweb.web import uicfg

uicfg.autoform_section.tag_subject_of(('*', 'container_etype', '*'), 'main', 'hidden')
uicfg.autoform_section.tag_subject_of(('*', 'container_parent', '*'), 'main', 'hidden')
uicfg.primaryview_section.tag_subject_of(('*', 'container_etype', '*'), 'hidden')
uicfg.primaryview_section.tag_subject_of(('*', 'container_parent', '*'), 'hidden')

uicfg.autoform_section.tag_object_of(('*', 'container_etype', '*'), 'main', 'hidden')
uicfg.autoform_section.tag_object_of(('*', 'container_parent', '*'), 'main', 'hidden')
uicfg.primaryview_section.tag_object_of(('*', 'container_etype', '*'), 'hidden')
uicfg.primaryview_section.tag_object_of(('*', 'container_parent', '*'), 'hidden')
