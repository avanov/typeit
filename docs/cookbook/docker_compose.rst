.. _Cookbook:

Structuring Docker Compose Config
=================================

Sketching
---------

Let's assume you have a docker-compose config to spin up Postgres and Redis backends:

.. code-block:: YAML

    # Source code of ./docker-compose.yml
    ---
    version: "2.0"
    services:
      postgres:
        image: postgres:11.3-alpine
        environment:
          POSTGRES_USER: user
          POSTGRES_PASSWORD: password
          POSTGRES_DB: database
        ports:
          - 5433:5432

      redis:
        image: redis:5.0.4-alpine
        ports:
          - 6380:6379

Let's also assume that you want to manipulate this config from your Python
program, but you don't like to deal with it as a dictionary, because your
IDE doesn't hint you about available keys in dictionaries, and because
you don't want to accidentally mix up host/guest ports of your containerized services.
Hence, you decide to parse this config and put it into an appropriate
Python representation that you would call ``DockerConfig``.

And because writing boilerplate logic of this kind is always tiresome and is error-prone when done manually,
you employ ``typeit`` for the task and do preliminary sketching with it:

.. code-block:: bash

    $ typeit gen -s ./docker-compose.yml > ./docker_config.py

The command will generate ``./docker_config.py`` with definitions similar to this:

.. code-block:: python

    # Source code of ./docker_config.py

    from typing import Any, NamedTuple, Optional, Sequence
    from typeit import TypeConstructor


    class ServicesRedis(NamedTuple):
        image: str
        ports: Sequence[str]


    class ServicesPostgresEnvironment(NamedTuple):
        POSTGRES_USER: str
        POSTGRES_PASSWORD: str
        POSTGRES_DB: str


    class ServicesPostgres(NamedTuple):
        image: str
        environment: ServicesPostgresEnvironment
        ports: Sequence[str]


    class Services(NamedTuple):
        postgres: ServicesPostgres
        redis: ServicesRedis


    class Main(NamedTuple):
        version: str
        services: Services


    mk_main, serialize_main = TypeConstructor ^ Main

Neat! This already is a good enough representation to play with, and we can verify that
it does work as expected:

.. code-block:: python

    # Source code of ./__init__.py

    import yaml
    from . import docker_config as dc

    with open('./docker-compose.yml', 'rb') as f:
        config_dict = yaml.safe_load(f)

    config = dc.mk_main(config_dict)
    assert isinstance(config, dc.Main)
    assert isinstance(config.services.postgres, dc.ServicesPostgres)
    assert config.services.postgres.ports == ['5433:5432']
    assert dc.serialize_main(config) == conf_dict

Now, let's refactor it a bit, so that ``Main`` becomes ``DockerConfig`` as we wanted,
and ``DockerConfig.version`` is restricted to ``"2.0"`` and ``"2.1"`` only (and doesn't allow any random string):

.. code-block:: python

    # Source code of ./__init__.py

    from typing import Literal
    # from typing_extensions import Literal  # on python < 3.8

    class DockerConfig(NamedTuple):
        version: Literal['2.0', '2.1']
        services: Services


    mk_config, serialize_config = TypeConstructor ^ DockerConfig

Looks good! There is just one thing that we still want to improve - service ports.
And for that we need to extend our ``TypeConstructor``.

Extending
---------

At the moment our ``config.services.postgres.ports`` value is represented as a list of one string element ``['5433:5432']``.
It is still unclear which of those numbers belongs to what endpoint in a host <-> container network binding. You may
remember Docker documentation saying that the actual format is ``"host_port:container_port"``,
however, it is inconvenient to spread this implicit knowledge across your Python codebase. Let's annotate
these ports by introducing a new data type:

.. code-block:: python

    # Source code of ./docker_config.py

    class PortMapping(NamedTuple):
        host_port: int
        container_port: int

We want to use this type for port mappings instead of ``str`` in ``ServicesRedis`` and ``ServicesPostgres`` definitions:

.. code-block:: python

    # Source code of ./docker_config.py

    class ServicesRedis(NamedTuple):
        image: str
        ports: Sequence[PortMapping]


    class ServicesPostgres(NamedTuple):
        image: str
        environment: ServicesPostgresEnvironment
        ports: Sequence[PortMapping]

This looks good, however, our type constructor doesn't know anything about conversion rules
between a string value that comes from the YAML config and ``PortMapping``.
We need to explicitly define this rule:

.. code-block:: python

    # Source code of ./docker_config.py

    import typeit

    class PortMappingSchema(typeit.schema.primitives.Str):
        def deserialize(self, node, cstruct: str) -> PortMapping:
            """ Converts input string value ``cstruct`` to ``PortMapping``
            """
            ports_str = super().deserialize(node, cstruct)
            host_port, container_port = ports_str.split(':')
            return PortMapping(
                host_port=int(host_port),
                container_port=int(container_port)
            )

        def serialize(self, node, appstruct: PortMapping) -> str:
            """ Converts ``PortMapping`` back to string value suitable for YAML config
            """
            return super().serialize(
                node,
                f'{appstruct.host_port}:{appstruct.container_port}'
            )

Next, we need to tell our type constructor that all ``PortMapping`` values
can be constructed with ``PortMappingSchema`` conversion schema:

.. code-block:: python

    # Source code of ./docker_config.py

    Typer = typeit.TypeConstructor & PortMappingSchema[PortMapping]

We named the new extended type constructor ``Typer``, and we're done with the task!
Let's take a look at the final result.

Final Result
------------

Here's what we get as the final solution for our task:

.. code-block:: python

    # Source code of ./docker_config.py

    from typing import NamedTuple, Sequence
    from typing import Literal
    # from typing_extensions import Literal  # on python < 3.8

    import typeit


    class PortMapping(NamedTuple):
        host_port: int
        container_port: int


    class PortMappingSchema(typeit.schema.primitives.Str):
        def deserialize(self, node, cstruct: str) -> PortMapping:
            """ Converts input string value ``cstruct`` to ``PortMapping``
            """
            ports_str = super().deserialize(node, cstruct)
            host_port, container_port = ports_str.split(':')
            return PortMapping(
                host_port=int(host_port),
                container_port=int(container_port)
            )

        def serialize(self, node, appstruct: PortMapping) -> str:
            """ Converts ``PortMapping`` back to string value suitable
            for YAML config
            """
            return super().serialize(
                node,
                f'{appstruct.host_port}:{appstruct.container_port}'
            )


    class ServicesRedis(NamedTuple):
        image: str
        ports: Sequence[PortMapping]


    class ServicesPostgresEnvironment(NamedTuple):
        POSTGRES_USER: str
        POSTGRES_PASSWORD: str
        POSTGRES_DB: str


    class ServicesPostgres(NamedTuple):
        image: str
        environment: ServicesPostgresEnvironment
        ports: Sequence[PortMapping]


    class Services(NamedTuple):
        postgres: ServicesPostgres
        redis: ServicesRedis


    class DockerConfig(NamedTuple):
        version: Literal['2', '2.1']
        services: Services


    Typer = typeit.TypeConstructor & PortMappingSchema[PortMapping]
    mk_config, serialize_config = Typer ^ DockerConfig


Let's test it!

.. code-block:: python

    # Source code of ./__init__.py

    import yaml
    from . import docker_config as dc

    with open('./docker-compose.yml', 'rb') as f:
        config_dict = yaml.safe_load(f)

    config = dc.mk_config(config_dict)

    assert isinstance(config, dc.DockerConfig)
    assert isinstance(config.services.postgres, dc.ServicesPostgres)
    assert isinstance(config.services.postgres.ports[0], dc.PortMapping)
    assert isinstance(config.services.redis.ports[0], dc.PortMapping)
    assert dc.serialize_config(config) == config_dict


Notes
-----

* Under the hood, ``typeit`` relies on `Colander <https://docs.pylonsproject.org/projects/colander/en/latest/>`_ - a schema
  parsing and validation library that you may need to familiarise yourself with in order to understand ``PortMappingSchema``
  definition.
