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

complemented by the container configuration (in ``mycube/__init__.py``):

.. code-block:: python

    from cubes.container import ContainerConfiguration

    PROJECT_CONTAINER = ContainerConfiguration('Project', 'project')


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

    def post_build_callback(schema):
        from cubes.mycube import PROJECT_CONTAINER
        PROJECT_CONTAINER.define_container(schema)

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

    from cubicweb.entities import AnyEntity

    from cubes.mycube import PROJECT_CONTAINER

    class Project(AnyEntity):
        __regid__ = 'Project'
        container_config = PROJECT_CONTAINER


 def registration_callback(vreg):
     vreg.register_all(globals().values(), __name__)
     project_protocol = PROJECT_CONTAINER.build_container_protocol(vreg.schema)
     vreg.register(project_protocol)

Here we perform two things:

* we attach the container configuration on the entity type (yams cannot
  currently host that piece of information) for later use,

* we instantiate the ContainerProtocol adapter with a proper selector set,
  thanks to the ``build_container_protocol`` method in
  ``registration_callback``. This adapter will help the hooks for the
  maintenance of the container relations (`<container_rtype>` and
  `container_parent` if it exists). It may also be used in views (or where it
  fits) to compute the container parent and the container root entities of any
  containerised entity.


Hooks
.....

The hooks will set up the container relations at edition time. The
``build_container_hooks`` method of the configuration object will instantiate
hooks responsible of maintaining the `container` relation at edition time.

.. code-block:: python

    def registration_callback(vreg):
        from cubes.mycube import PROJECT_CONTAINER
        schema = vreg.schema
        for hookcls in PROJECT_CONTAINER.build_container_hooks(schema):
            vreg.register(hookcls)

