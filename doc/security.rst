Using a container as a security scope
.....................................

The general idea is to define a security policy at the container root
entity level and then automate the assignation of __permissions__ rules
on each contained etype and rtype.

The concepts are provided along with a fully working example.

Initial data model
------------------

The container root entity carries permissions, e.g.:

.. code-block:: python

 class Project(EntityType):
     name = String(required=True)
     __permissions__ = {
         'read':   ('managers', ERQLExpression('U canread X')),
         'add':    ('managers', 'users'),
         'update': ('managers', ERQLExpression('U canwrite X')),
         'delete': ('managers', ERQLExpression('U canwrite X'))
     }

 # a standard read-write permission scheme
 class canread(RelationDefinition):
     subject = 'CWUser'
     object = 'Project'

 class canwrite(RelationDefinition):
     subject = 'CWUser'
     object = 'Project'

Here the `canread` and `canwrite` relations are an example of a
possible simple quasi-standard permission strategy.

What is not (yet) expressed there is that for all entities and
relations within the container we want the ('CWUser', 'canread',
'Project') and ('CWUser', 'canwrite', 'Project') to ultimately control
what is permissible for the application users. But let's complete our
schema first.

.. code-block:: python

 class Version(EntityType):
     __unique_together__ = [('name', 'version_of')]
     name = String(required=True, maxsize=16)
     version_of = SubjectRelation('Project', cardinality='1*',
                                  composite='object', inlined=True)

 class Ticket(EntityType):
     name = String(required=True, maxsize=64)
     description = String(required=True)
     concerns = SubjectRelation('Project', cardinality='1*',
                                 composite='object', inlined=True)
     done_in_version = SubjectRelation('Version', cardinality='?*')

 class Patch(EntityType):
     name = String(required=True, maxsize=64)
     content = SubjectRelation('File', cardinality='1*', inlined=True)
     implements = SubjectRelation('Ticket', cardinality='1*',
                                  composite='object', inlined=True)


Automating the entity types permissions
---------------------------------------

Rather than setting by hand the permissions on each entity type, we
prefer to automate this. One good argument for automation here is to
keep the code dry_.

.. _dry: http://en.wikipedia.org/wiki/Don%27t_repeat_yourself

Let's define a simple class decorator for the Project sub-entities:

.. code-block:: python

 def project(etypeclass):
      etypeclass.__permissions__ = {
          'read':   ('managers', ERQLExpression('U canread P, X project P')),
          'add':    ('managers', 'users'), # can't really do it there
          'update': ('managers', ERQLExpression('U canwrite P, X project P')),
          'delete': ('managers', ERQLExpression('U canwrite P, X project P'))
       }
       return etypeclass

We can now just decorate `Version`, `Ticket` and `Patch` like this:

.. code-block:: python

 @project
 class Version(...):
     ...

That was easy!


Automating the relation definitions permissions
-----------------------------------------------

Now we must also establish relations permissions. We may consider
three kinds of relations with respect to the container:

* composite/structural relations (`version_of`, `concerns`,
  `implements`) that define the container skeleton,

* inner relations (e.g. `done_in_version`), linking entities within
  the container,

* border crossing relations (e.g. `content`), linking container
  entities to the outside world.


The structural relations come first as they provide the missing policy
for the `add` rule on entity types. Indeed we can't have an `add` rule
on the entity type itself because before the entity is created the
path to the container is (obviously...) not established yet.

Their permissions could look like this:

.. code-block:: python

 __permissions__ = {
     'read':   ('managers', 'users'),
     'add':    ('managers', RRQLExpression('O project P, U canwrite P')),
     'delete': ('managers', RRQLExpression('O project P, U canwrite P')),
 }

Here the `add` permission will effectively control the ability to add
the subject entity (e.g. the `Patch`), by traversing at relation
creation time the path to the container through the relation object
(e.g. here a `Ticket` entity).

This will _always_ work because the moment we do this the ticket
entity and, to be more general, the whole upward path (entities,
relations) to the container already exists, by construction.

This is good.

However if we want to automate this there's a slight problem. The
relation to the parent entity might be defined as e.g. ('Patch',
'implements', 'Ticket'), but also as ('Ticket', 'has_patch', 'Patch').

If we had the latter case, we would have to rewrite::

 RRQLExpression('O project P, U canread P')

as::

 RRQLExpression('S project P, U canread P')

.. note::

 S, O and U are prebound variables in an RRQLExpression. They refer
 to, respectively the subject, the object (of the considered relation)
 and the current user.

We can step back a bit and propose a parametrised security rule for
now, e.g.:

.. code-block:: python

 def container_rtypes_perms(role_to_container):
     # role_to_container is either 'S' or 'O'
     return {
         'read':   ('managers', 'users', 'guests'),
         'add':    ('managers',
                    RRQLExpression('%s project P, U canwrite P' % role_to_container)),
         'delete': ('managers',
                    RRQLExpression('%s project P, U canwrite P' % role_to_container)),
      }

Before we go on and see how to exploit this, we must tackle another
little difficulty. Let's consider for instance the ('Version',
'version_of', 'Project') relation. Here the `role_to_container`, that
is 'O', is actually the container itself. Hence it makes no sense to
spell 'O project P' because the `project` container relation is never
on the root entity itself. This is really a special case and we must
deal with it. Let's write the following definition:

.. code-block:: python

 def near_container_rtype_perms(role_to_container):
     # role_to_container is either 'S' or 'O'
     return {
         'read':   ('managers', 'users', 'guests'),
         'add':    ('managers',
                    RRQLExpression('U canwrite %s' % role_to_container)),
         'delete': ('managers',
                    RRQLExpression('U canwrite %s' % role_to_container)),
      }


Now is the time to decorate the relations with these definitions. The
`secutils` module provides a function to do this. The following snippet
shows how to use it in our cube's schema.py module. We assume the
previous definitions are already present in the module scope.

.. code-block:: python

 def setup_project_security(schema):
     from cubes.codereview.entities.project import Project
     setup_container_rtypes_security(schema,
                                     Project,
                                     near_container_rtypes_perms=near_container_rtype_perms,
                                     inner_rtypes_perms=container_rtypes_perms,
                                     border_rtypes_perms=container_rtypes_perms)

 def post_build_callback(schema):
     setup_project_security(schema)


.. note::

 As can be seen, we provide container_rtypes_perms to both
 `inner_rtypes_perms` and `border_rtypes_perms`. Not all security
 models need the extra flexibility.

The permission functions we have previously written will be used by a
schema-walking algorithm that computes the `role_to_container` (and
never gets it wrong, unlike a programmer) and assigns the permission
rules to the relevant relations.


Handling special cases
----------------------

Let's formulate a problem: we would like the ('Patch', 'content',
'File') relation to be immutable if the patch is linked to a ticket
that is in a version.

We could formulate the relation as such:

.. code-block:: python

 class content(RelationDefinition):
     subject = 'Patch'
     object = 'File'
     __permissions__ = {
         'read':   ('managers', RRQLExpression('S project P, U canread P')),
         'add':    ('managers', RRQLExpression('S project P, U canwrite P')),
         'delete': ('managers', RRQLExpression('S implements T, NOT T done_in_version V'))
     }

The problem with this until now is that it will be overridden by the
call to `setup_project_security`.

Hence we use a specific trick, the `PERM` marker and the `PERMS`
mapping (from marker to permission ruleset). Here's how it will be
used:

.. code-block:: python

 PERMS['patch-content'] = {
     'read':   ('managers', RRQLExpression('S project P, U canread P')),
     'add':    ('managers', RRQLExpression('S project P, U canwrite P')),
     'delete': ('managers', RRQLExpression('S implements T, NOT T done_in_version V'))
 }

 class content(RelationDefinition):
     subject = 'Patch'
     object = 'File'
     __permissions__ = PERM('patch-content')

This is understood by the schema-walking function as an ad-hoc
override that must be not be replaced.
