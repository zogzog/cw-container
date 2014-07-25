from cubicweb.entities import AnyEntity
from cubicweb.predicates import is_instance

from cubes.container.entities import ContainerClone, MultiParentProtocol

class DiamondClone(ContainerClone):
    __select__ = is_instance('Diamond', 'Mess')
    rtypes_to_skip = ()
    etypes_to_skip = ()

class Multiparent(MultiParentProtocol):
    __select__ = is_instance('IAmAnAttributeCarryingRelation')


def dc_title(self):
    basetitle = self.e_schema.type
    padapter = self.cw_adapt_to('Container')
    if padapter:
        parent = padapter.parent
        if parent:
            return '%s -> %s' % (basetitle, parent.dc_title())
        return '%s -> ()' % basetitle
    return basetitle
AnyEntity.dc_title = dc_title


class Diamond(AnyEntity):
    __regid__ = 'Diamond'

    def dc_title(self):
        return 'Diamond (%s)' % self.name or '<anonymous>'
