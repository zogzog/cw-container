from cubes.container import ContainerConfiguration

CIRCUS_CONTAINER = ContainerConfiguration('Circus', 'circus', subcontainers=('Menagerie', ))
MENAGERIE_CONTAINER = ContainerConfiguration('Menagerie', 'zoo')
