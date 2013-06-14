=========
Container
=========

Definition & purpose
--------------------

A container is a reification of a recurring schema pattern.

A container is a rooted directed acyclic graph of entity types and
relation types. It is defined by a root entity type and composite
relations stemming directly and indirectly from this root.

The container contains:

* all composite/composed entity types transitively reachable from the
  root,

* all relation definitions between two entities belonging to the
  container.

Typical usages include:

* deleting a whole container in one operation

* cloning

* importing from and exporting to file formats (such as csv or excel)

* being a security scope

Deletion and cloning are supported out of the box currently. Container
serializers may be available as extension cubes.


Structure details
-----------------

Link to the container
.....................

All entity types within a container participate in a `<container>`
relation type::

 <Entity> <container> <Container>


The `<container>` rtype is automatically maintained by a creation
hook.


Link to parent entities
.......................

All entities within a container have at least one `parent`.

Within a container, there may exist a `container_parent` rtype that
defines a concrete parent/child relationship leading up to the
container root. The `container_parent` relation definitions are
created only when there exists several possible parents. When there
exists only one, schema reflection is used to find the actual parent.

This is also automatically set by a hook triggered on any container
constituent rtype.

While several composite relations can be allowed between an entity
and container entities, at most one is allowed to be valued at
a given time for normal entities.

However there exist use cases for entities that are simultaneously
engaged in composite relations with several other entities. The most
common use case is the representation of n-ary relations or
attribute-carrying relations, for which there is no first-class
support in CubicWeb.

In the later case, the `container_parent` is set by default following
the first established composite relation, but the parentage behaviour
can be customized through the `container.multiple_parents` adapter.


Outward links
.............

Non composite relations from contained entities to non contained
entities are boundary relations.


Operations
----------

A clone operation is defined over a parametrised subset of
`<container>`. The scope of a clone is computed from an extensive etype
list or using rtype boundaries.


Security container
------------------

A security module can provide a simple security model where granting
permissions (or roles) to container related user groups gives them these
permissions accross all contained entities.

More complicated security models can be grafted on containers but this
is out of scope.


Setting up a container
----------------------

This section is illustrated by the container cube's test suite. You
will find all the relevant examples in `test/data`.

These are the usual steps involved in a container definition:

* schema definition: see test/data/schema.py

  The test schema defines two containers, with at least one shared
  entity type (which does not mean that its instances will be allowed
  to live in both containers at the same time!).

  For each container structure, a call to the `define_container`
  function is made: this will build the `container` relations and the
  `container_parent` if they are needed.

* schema tests: having tests suchs as the ones in unittest_schema in
  your container-using cubes is a very important non-regression asset
  (esp. against unvoluntary container definition, and to help diagnose
  container behaviour problems).

  Having at least test_static_structure and test_etypes_rtypes is
  extremely useful, even very early in the development of a container,
  as it helps spot mistakes in the structure definition.

* hooks: see test/data/hooks.py

  The SetContainerParent and SetContainerRelation hooks must be setup
  along with your container definitions.

  This is almost automatic as the set_container_parent_rtypes_hook and
  set_container_parent_rtypes_hook functions compute the exact rtypes
  set needed for the selectors.

* entities and adapters: see test/data/entities.py

  As of today, entity classes of the CubicWeb `orm` are used to
  customize a container definition.

  The `container_rtype` attribute gives a name to the concrete
  `<container_rtype>` relation.

  The `container_skiprtypes` attribute is a tuple containing rtypes
  not to follow when defining a container or operating on it. Security
  or workflow information (as examplified by `local_group` and
  `wf_info_for`) may indeed be excluded from most operations and be
  kept under the control of specific hooks.

  The `ContainerProtocol` must be set up an all container etypes. This
  is the main API to get to a container or a parent entity within a
  container.

  The `MultiParentProtocol` can be optionally set up for these
  entities that may have many parents at the same time. The container
  cube makes no special assumption about what to do and gives its
  users this specific entry point to implement custom behaviour.

  Indeed the `MultiParentProtocol` will be called from the
  `SetContainerParent` hook when such an entity already has one parent
  set.


Building a simple yet realistic example
---------------------------------------

Schema
......

Let's start with a schema:

.. code-block:: python

 from yams.buildobjs import SubjectRelation, String, Date, RelationDefinition
 from cubicweb.schema import WorkflowableEntityType, RichString

 from cubes.container import utils

 class Project(WorkflowableEntityType):
     name = String()
     description = RichString()
     uses = SubjectRelation('Project')

 class Version(WorkflowableEntityType):
    num = String(description=_('release number'))
    description = RichString()
    publication_date = Date(description=_('publication date'))
    version_of = SubjectRelation('Project', cardinality='1*', composite='object')

 class Ticket(WorkflowableEntityType):
     summary = String()
     priority = String(vocabulary=[_('important'), _('normal'), _('minor')])
     type = String(vocabulary=[_('bug'), _('enhancement'), _('task')])
     concerns = SubjectRelation('Project', cardinality='1*', composite='object')
     done_in = SubjectRelation('Version', cardinality='1*')

 class attachment(RelationDefinition):
     subject = ('Project', 'Version', 'Ticket')
     object = 'File'
     cardinality = '*1'
     composite = 'subject'

 def post_build_callback(schema):
    utils.define_container(schema, 'Project', 'project')


And now, let's discuss. There are 4 (four) entity types here:
`Project`, `Version`, `Ticket` and `File`. The later is provided by
the `file` cube, which we need not expand on here.

These entity types can make a container:

* the root type would be `Project`

* the `concerns`, `version_of` and `attachment` relations define the
  DAG structure, implying `Ticket`, `Version` and `File` belong to the
  container.

By telling, in the `post_build_callback` schema function as such:

.. code-block:: python

  utils.define_container(schema, 'Project', 'project')

one actually defines the following:

* a `project` relation type that bind `Ticket`, `Version` and `File`
  to a `Project`

* a `container_parent` relation definition from `File` to `Ticket`,
  `Version` and `Project`


Entities
........

We now have to complement the schema declarations with a few more in
the entities.

.. code-block:: python

 from cubicweb.selectors import is_instance

 from cubes.container import utils
 from cubes.container.entities import Container, ContainerProtocol

 class Project(Container):
     __regid__ = 'Project'
     container_rtype = 'project'

 class ProjectContainer(ContainerProtocol):
     pass

 def registration_callback(vreg):
     vreg.register_all(globals().values(), __name__)
     _r, etypes = utils.container_static_structure(vreg.schema, 'Project', 'project')
     ProjectContainer.__select__ = (ProjectContainer.__select__ &
                                    is_instance('Project', *etypes))

Here we perform two things:

* we declare the `container_rtype` on the entity type (yams cannot
  currently host that piece of information) for later use,

* we put the right selector on the ContainerProtocol adapter. This
  adapter will help the hooks for the maintenance of the container
  relations (`<container_rtype>` and `container_parent` if it
  exists). It may also be used in views (or where it fits) to compute
  the container parent and the container root entities of any
  containerised entity.


Hooks
.....

The hooks will set up the container relations at edition time. Let's
have a look at some code.

.. code-block:: python

 from cubicweb.server.hook import match_rtype
 from cubes.container import hooks, utils

 class SetContainerParent(hooks.SetContainerParent):
     __select__ = utils.yet_unset()

 class SetContainerRelation(hooks.SetContainerRelation):
     __select__ = utils.yet_unset()


 def registration_callback(vreg):
     schema = vreg.schema
     rtypes = utils.set_container_parent_rtypes_hook(schema, 'Project', 'project')
     SetContainerParent.__select__ = Hook.__select__ & match_rtype(*rtypes)
     rtypes_m = utils.set_container_relation_rtypes_hook(schema, 'Project', 'project')
     SetContainerRelation.__select__ = Hook.__select__ & match_rtype(*rtypes)
     vreg.register(SetContainerParent)
     vreg.register(SetContainerRelation)


The `SetContainerParent` hook computes and sets the parent when a
`container_parent` relation is needed.

The `SetContainerRelation` hook computes and sets the
`<container_rtype>` relation at creation time for any containerised
entity.
