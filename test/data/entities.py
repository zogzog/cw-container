from cubicweb.predicates import is_instance

from cubes.container.entities import ContainerClone, MultiParentProtocol

class DiamondClone(ContainerClone):
    __select__ = is_instance('Diamond', 'Mess')
    rtypes_to_skip = ()
    etypes_to_skip = ()

class Multiparent(MultiParentProtocol):
    __select__ = is_instance('IAmAnAttributeCarryingRelation')

