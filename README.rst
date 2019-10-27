.. _badges:

.. image:: https://travis-ci.org/avanov/typeit.svg?branch=develop
    :target: https://travis-ci.org/avanov/typeit

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


**Development status: Beta**

Typeit
------

`typeit` brings typed data into your project.

.. code-block:: bash

    $ echo '{"first-name": "Hello", "initial": null, "last_name": "World"}' | typeit gen


The snipped above produces output similar to this:

.. code-block:: python

    from typing import Any, NamedTuple, Optional, Sequence
    from typeit import type_constructor


    class Main(NamedTuple):
        first_name: str
        initial: Optional[Any]
        last_name: str


    overrides = {
        Main.first_name: 'first-name',
    }


    mk_main, serialize_main = type_constructor & overrides ^ Main


Documentation
-------------

Documentation is hosted on ReadTheDocs: https://typeit.readthedocs.io/en/develop/


Test framework
--------------

Run existing test suite with

.. code::

   $ pytest
