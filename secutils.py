# copyright 2013-2014 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
"""Utilities to bolt security policies on a container

See documentation in doc/security.rst
"""
from cubicweb.server import ON_COMMIT_ADD_RELATIONS
from cubes.container import utils

class PERM(str):
    """ a marker for entity/relation permissions
    that will indicate a specific permission ruleset
    the container-walking algorithm (setup_security)
    MUST NOT override

    This works with the PERMS mapping, which associates a
    symbolic name to a permission rule, and the PERM object
    which must be used to reference such a rule in the
    __permission__ property of etypes/relations.

    Example::

     PERMS['MYRULE'] = {'read': ('managers', 'users'),
                        'add': ('managers',)
                        ... }
     PERMS['BABAR_RULE'] = { ... }

     class MyEntity(EntityType):
         __permissions__ = PERM('MYRULE')
         myrel = SubjectRelation('Babar',
                                 __permissions__=PERM('BABAR_RULE'))
    """

    def __new__(cls, string):
        self = str.__new__(cls, string)
        assert self in PERMS, '%s does not appear in %s' % (self, PERMS.keys())
        return self

    def copy(self):
        return self

# mapping from PERM to permissions objects
PERMS = {}

_PROCESSED_PERMISSION_RDEFS = set()

def setup_container_rtypes_security(schema,
                                    container_etypeclass,
                                    # permissions functions
                                    near_container_rtypes_perms,
                                    inner_rtypes_perms,
                                    border_rtypes_perms):

    cetype = container_etypeclass.__regid__
    skiprtypes = frozenset(container_etypeclass.container_skiprtypes)
    skipetypes = frozenset(container_etypeclass.container_skipetypes)
    subcontainers = container_etypeclass.container_subcontainers
    rtypes, etypes = utils.container_rtypes_etypes(schema,
                                                   cetype,
                                                   container_etypeclass.container_rtype,
                                                   skiprtypes=skiprtypes,
                                                   skipetypes=skipetypes,
                                                   subcontainers=subcontainers)

    # we palliate for the non-reflexivity of the container relation
    etypesplus = etypes | set([cetype])

    def rdefs_roles_to_container(rschema):
        """ computes a mapping of (subjet, object) to 'S' or 'O' role name
        giving the direction of the container root
        """
        rdefs_roles = {}
        for (subj, obj), rdef in rschema.rdefs.iteritems():
            if rdef.composite is None:
                # if both the subj/obj are in the container, we
                # default to the subject (it does not really matter)
                if subj.type in etypes:
                    rdefs_roles[(subj.type, obj.type)] = 'S'
                elif obj.type in etypes:
                    rdefs_roles[(subj.type, obj.type)] = 'O'

                continue

            # structural relations:
            # we must choose the side nearest to the container root
            # 'subject' => 'S', 'object' => 'O'
            # Both subj/obj must be in etypes
            if subj not in etypesplus and obj not in etypesplus:
                continue

            composite = subj if rdef.composite == 'subject' else obj
            # filter out subcontainer
            # any relation who defined a subcontainer as a composite
            # is not ours and its handling will be delegated
            if composite in subcontainers:
                continue

            # any relation that points to an etype which is not ours
            # (including ourselves) will be handled by someone else
            if composite not in etypesplus:
                continue

            rdefs_roles[(subj.type, obj.type)] = rdef.composite[:1].upper()
        return rdefs_roles

    def set_rdefs_perms(rschema, rdefs_roles, perms):
        """ for all collected rdefs, set the permissions
        using the perms('S' or 'O') callable
        """
        assert callable(perms)
        for (subj, obj), role in rdefs_roles.iteritems():
            rdef = rschema.rdefs[(subj, obj)]
            if rdef in _PROCESSED_PERMISSION_RDEFS:
                continue
            if isinstance(rdef.permissions, PERM):
                rdef.permissions = PERMS[rdef.permissions]
            else:
                rdef.permissions = perms(role)
            _PROCESSED_PERMISSION_RDEFS.add(rdef)

    # 1. internal rtypes
    for rtype in rtypes:
        ON_COMMIT_ADD_RELATIONS.add(rtype)
        rschema = schema[rtype]
        rdefs_roles = rdefs_roles_to_container(rschema)
        for role in ('subject', 'object'):
            if rschema.targets(role=role)[0].type == cetype:
                # a simpler form: S or O is the container
                # (this is a _correctness_ issue, not an optimisation)
                rtype_perms = near_container_rtypes_perms
                break
        else:
            rtype_perms = inner_rtypes_perms
        set_rdefs_perms(rschema, rdefs_roles, rtype_perms)

    # 2. border crossing rtypes
    for rtype in sorted(utils.border_rtypes(schema, etypes, rtypes|skiprtypes)):
        ON_COMMIT_ADD_RELATIONS.add(rtype)
        rschema = schema[rtype]
        rdefs_roles = rdefs_roles_to_container(rschema)
        set_rdefs_perms(rschema, rdefs_roles, border_rtypes_perms)
