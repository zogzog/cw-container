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
