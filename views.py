# copyright 2011-2014 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
from logilab.common.deprecation import deprecated

from cubicweb import onevent
from cubicweb.predicates import EClassPredicate
from cubicweb.web.views import uicfg

for rtype in ('container_etype', 'container_parent'):
    uicfg.primaryview_section.tag_subject_of(('*', rtype, '*'), 'hidden')
    uicfg.primaryview_section.tag_object_of(('*', rtype, '*'), 'hidden')

    uicfg.autoform_section.tag_subject_of(('*', rtype, '*'), 'main', 'hidden')
    uicfg.autoform_section.tag_object_of(('*', rtype, '*'), 'main', 'hidden')


class is_container(EClassPredicate):
    etypes = set()

    def score_class(self, eclass, req):
        return (eclass.__name__ in self.etypes) * 4

@deprecated('[container 2.7] this is now automatic '
            'and need not be called any longer')
def setup_container_ui(vreg):
    pass

def registration_callback(vreg):
    @onevent('after-registry-reload')
    def setup_ui():
        # we reimport here to be robust against module reference mess after a reload
        from cubes.container import config
        from cubicweb.web.views import uicfg
        afs = uicfg.autoform_section
        pvs = uicfg.primaryview_section

        for cetype in config.Container.all_etypes():
            try:
                is_container.etypes.add(cetype)
            except:
                # we are in the middle of a reload for e.g. "i18ncube" ... :-/
                return

            conf = config.Container.by_etype(cetype)

            # NOTE NOTE NOTE
            # In theory, this should be handled by just declaring conf.crtype as META_RTYPE
            # which is actually done in config.py in define_container.
            #
            # But, the meta-ness is not serialized in the schema and only
            # because of devtools/testlib behaviour do the META_RTYPE gets properly updated.
            #
            # Hence we re-do this (in theory redundant) initialisation to help
            # the "ctl start <myapp>" use case ...
            for etype in conf.etypes:
                for role in ('subject', 'object'):
                    pvs.tag_relation((etype, conf.crtype, conf.cetype, role), 'hidden')
                    for section in ('main', 'muledit', 'inlined'):
                        afs.tag_relation((etype, conf.crtype, conf.cetype, role), section, 'hidden')
