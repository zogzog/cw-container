from cubes.container import ContainerConfiguration

PROJECT_CONTAINER = ContainerConfiguration('Project', 'project',
                                           subcontainers=('Version',))

VERSION_CONTAINER = ContainerConfiguration('Version', 'version')
