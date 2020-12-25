.. _badges:

.. image:: https://github.com/avanov/typeit/workflows/CI/badge.svg?branch=develop
    :target: https://github.com/avanov/typeit/actions?query=branch%3Adevelop

.. image:: https://coveralls.io/repos/github/avanov/typeit/badge.svg?branch=develop
    :target: https://coveralls.io/github/avanov/typeit?branch=develop

.. image:: https://requires.io/github/avanov/typeit/requirements.svg?branch=master
    :target: https://requires.io/github/avanov/typeit/requirements/?branch=master
    :alt: Requirements Status

.. image:: https://readthedocs.org/projects/typeit/badge/?version=latest
    :target: http://typeit.readthedocs.org/en/latest/
    :alt: Documentation Status

.. image:: http://img.shields.io/pypi/v/typeit.svg
    :target: https://pypi.python.org/pypi/typeit
    :alt: Latest PyPI Release


Typeit
------

**typeit** infers Python types from a sample JSON/YAML data, and provides you with the tools
for serialising and parsing it. It also provides you with smart constructors for arbitrarily nested data structures.
The library works superb on Python 3.7 and above.

Start using it by generating types for your JSON payloads:

.. code-block:: bash

    $ echo '{"first-name": "Hello", "initial": null, "last_name": "World"}' | typeit gen


The snipped above produces output similar to this:

.. code-block:: python

    from typing import Any, NamedTuple, Optional, Sequence
    from typeit import TypeConstructor


    class Main(NamedTuple):
        first_name: str
        initial: Optional[Any]
        last_name: str


    overrides = {
        Main.first_name: 'first-name',
    }


    mk_main, serialize_main = TypeConstructor & overrides ^ Main

Use these functions to construct and serialize your payloads:

.. code-block:: python

    payload = {"first-name": "Hello", "initial": None, "last_name": "World"}

    data = mk_main(payload)
    assert isinstance(data, Main)
    assert serialize_main(data) == payload


Documentation
-------------

Documentation is hosted on ReadTheDocs: https://typeit.readthedocs.io/en/develop/


Test framework
--------------

Run existing test suite with

.. code::

   $ pytest


Changelog
---------

See `CHANGELOG <https://github.com/avanov/typeit/blob/master/CHANGELOG.rst>`_.
