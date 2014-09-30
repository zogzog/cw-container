Building a simple yet realistic example
---------------------------------------

Schema
......

Let's start with a schema:

.. code-block:: python

 from yams.buildobjs import SubjectRelation, String, Date, RelationDefinition
 from cubicweb.schema import WorkflowableEntityType, RichString

 from cubes.container import config

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
    project = config.Container('Project', 'project')
    project.define_container(schema)


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

    project = config.Container('Project', 'project')
    project.define_container(schema)

one actually defines the following:

* a `project` relation type that bind `Ticket`, `Version` and `File`
  to a `Project`

* a `container_parent` relation definition from `File` to `Ticket`,
  `Version` and `Project`


