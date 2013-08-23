"""cubicweb-container application package

provides "generic container" services
"""

from cubicweb import schema

schema.META_RTYPES.update(('container_etype', 'container_parent'))
