from cubes.container import ContainerConfiguration

PROJECT_CONTAINER = ContainerConfiguration('Project', 'project',
                                           subcontainers=('Folder',))
FOLDER_CONTAINER = ContainerConfiguration('Folder', 'folder_root')
