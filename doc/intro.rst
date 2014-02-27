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
structural rtype.

While several composite relations can be allowed between an entity
and container entities, at most one is allowed to be valued at
a given time for *normal* entities.

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
entities are border relations.


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

  The SetContainerRelation hooks must be setup along with your
  container definitions.

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
  `SetContainerRelation` hook when such an entity already has one parent
  set.


