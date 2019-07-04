Quickstart Guide
================


.. CAUTION::

    The project is in a beta development status, and a few public
    APIs may change in a backward-incompatible manner.


``typeit`` supports Python 3.6+.


Installation
------------

.. code-block:: bash

    $ pip install typeit


Using CLI tool
--------------

Once installed, ``typeit`` provides you with a CLI tool that allows you to generate a prototype
Python structure of a JSON/YAML data that your app operates with.

For example, try the following snippet in your shell:

.. code-block:: bash

    $ echo '{"first-name": "Hello", "initial": null, "last_name": "World"}' | typeit gen


You should see output similar to this:

.. code-block:: python

    from typing import NamedTuple, Dict, Any, List, Optional
    from typeit import type_constructor


    class Main(NamedTuple):
        first_name: str
        initial: Optional[Any]
        last_name: str


    overrides = {
        Main.first_name: 'first-name',
    }


    mk_main, serialize_main = type_constructor & overrides ^ Main


You can use this snippet as a starting point to improve further.
For instance, you can clarify the ``Optional`` type of the ``Main.initial`` attribute,
and rename the whole structure to better indicate the nature of the data:

.. code-block:: python

    # ... imports ...

    class Person(NamedTuple):
        first_name: str
        initial: Optional[str]
        last_name: str


    overrides = {
        Person.first_name: 'first-name',
    }


    mk_person, serialize_person = type_constructor & overrides ^ Person


``typeit`` will handle creation of the constructor ``mk_person :: Dict -> Person`` and the serializer
``serialize_person :: Person -> Dict`` for you.

``type_constructor & overrides`` produces a new type constructor that takes overrides into consideration,
and ``type_constructor ^ Person`` reads as "type constructor applied to the Person structure" and essentially
is the same as ``type_constructor(Person)``, but doesn't require parentheses around overrides (and extensions):

.. code-block:: python

    (type_constructor & overrides & extension & ...)(Person)


Overrides
---------

.. CAUTION::

    This functionality may change in a backward-incompatible manner.


As you might have noticed in the example above, ``typeit`` generated a snippet with
a dictionary called ``overrides``, which is passed to the ``type_constructor`` alongside
our ``Person`` type:

.. code-block:: python

    overrides = {
        Person.first_name: 'first-name',
    }


    mk_person, serialize_person = type_constructor & overrides ^ Person


This is the way we can indicate that our Python structure has different field
names than the original JSON payload. ``typeit`` code generator created this
dictionary for us because the ``first-name`` attribute of the JSON payload is
not a valid Python variable name (dashes are not allowed in Python variables).

Instead of relying on automatic dasherizing of this attribute (for instance, with a help of
`inflection <https://inflection.readthedocs.io/en/latest/>`_ package), which rarely works
consistently across all possible corner cases, ``typeit`` explicitly
provides you with a reference point in the code, that you can track and refactor with
Intelligent Code Completion tools, should that necessity arise.

You can use the same ``overrides`` object to specify rules for attributes of
any nested types, for instance:

.. code-block:: python

    class Address(NamedTuple):
        street: str
        city: str
        postal_code: str


    class Person(NamedTuple):
        first_name: str
        initial: Optional[str]
        last_name: str
        address: Optional[Address]


    overrides = {
        Person.first_name: 'first-name',
        Address.postal_code: 'postal-code',
    }


    mk_person, serialize_person = type_constructor & overrides ^ Person


Handling errors
---------------

Let's take the snippet above and use it with incorrect input data. Here is how we would
handle the errors:

.. code-block:: python

    invalid_data = {'initial': True}

    try:
        person = mk_person(invalid_data)
    except typeit.Error as err:
        for e in err:
            print(f'Invalid data for `{e.path}`; {e.reason}: {repr(e.sample)} was passed')

If you run it, you will see an output similar to this::

    Invalid data for `first-name`; Required: None was passed
    Invalid data for `initial`; None of the expected variants matches provided data: True was passed
    Invalid data for `last_name`; Required: None was passed

Instances of ``typeit.Error`` adhere iterator interface that you can use to iterate over all
parsing errors that caused the exception.

Supported types
---------------

* ``bool``
* ``int``
* ``float``
* ``str``
* ``dict``
* ``set`` and ``frozenset``
* ``typing.Any`` passes any value as is
* ``typing.Union`` including nested structures
* ``typing.Sequence``, ``typing.List`` including generic collections with ``typing.TypeVar``.
* ``typing.Set`` and ``typing.FrozenSet``
* ``typing.Tuple``
* ``typing.Dict``
* ``typing.Mapping``
* ``typeit.sums.SumType``
* ``enum.Enum`` derivatives
* ``pathlib.Path`` derivatives
* ``typing_extensions.Literal``
* ``pyrsistent.typing.PVector``
* ``pyrsistent.typing.PMap``
* Regular classes with annotated ``__init__`` methods (`dataclasses.dataclass` are supported as a consequence of this).


Sum Type
--------

There are many ways to describe what a Sum Type (Tagged Union) is. Here's just a few of them:

* `Wikipedia <https://en.wikipedia.org/wiki/Tagged_union>`_ describes it as "a data structure used
  to hold a value that could take on several different, but fixed, types.
  Only one of the types can be in use at any one time, and a tag explicitly indicates which one
  is in use. It can be thought of as a type that has several “cases”, each of which should be handled
  correctly when that type is manipulated";

* or you can think of Sum Types as data types that have more than one constructor, where each constructor
  accepts its own set of input data;

* or even simpler, as a generalized version of Enums, with some extra features.

``typeit`` provides a limited implementation of Sum Types, that have functionality similar to default Python Enums,
plus the ability of each tag to hold a value.

A new SumType is defined with the following signature:

.. code-block:: python

    from typeit.sums import SumType

    class Payment(SumType):
        class Cash:
            amount: Money

        class Card:
            amount: Money
            card: CardCredentials

        class Phone:
            amount: Money
            provider: MobilePaymentProvider

        class JustThankYou:
            pass


``Payment`` is a new Tagged Union (which is another name for a Sum Type, remember), that consists
of four distinct possibilities: ``Cash``, ``Card``, ``Phone``, and ``JustThankYou``.
These possibilities are called tags (or variants, or constructors) of ``Payment``.
In other words, any instance of ``Payment`` is either ``Cash`` or ``Card`` or ``Phone`` or ``JustThankYou``,
and is never two or more of them at the same time.

Now, let's observe the properties of this new type:

.. code-block:: python

    >>> adam_paid = Payment.Cash(amount=Money('USD', 10))
    >>> jane_paid = Payment.Card(amount=Money('GBP', 8),
    ...                          card=CardCredentials(number='1234 5678 9012 3456',
    ...                                               holder='Jane Austen',
    ...                                               validity='12/24',
    ...                                               secret='***'))
    >>> fred_paid = Payment.JustThankYou()
    >>>
    >>> assert type(adam_paid) is type(jane_paid) is type(fred_paid) is Payment
    >>>
    >>> assert isinstance(adam_paid, Payment)
    >>> assert isinstance(jane_paid, Payment)
    >>> assert isinstance(fred_paid, Payment)
    >>>
    >>> assert isinstance(adam_paid, Payment.Cash)
    >>> assert isinstance(jane_paid, Payment.Card)
    >>> assert isinstance(fred_paid, Payment.JustThankYou)
    >>>
    >>> assert not isinstance(adam_paid, Payment.Card)
    >>> assert not isinstance(adam_paid, Payment.JustThankYou)
    >>>
    >>> assert not isinstance(jane_paid, Payment.Cash)
    >>> assert not isinstance(jane_paid, Payment.JustThankYou)
    >>>
    >>> assert not isinstance(fred_paid, Payment.Cash)
    >>> assert not isinstance(fred_paid, Payment.Card)
    >>>
    >>> assert not isinstance(adam_paid, Payment.Phone)
    >>> assert not isinstance(jane_paid, Payment.Phone)
    >>> assert not isinstance(fred_paid, Payment.Phone)
    >>>
    >>> assert Payment('Phone') is Payment.Phone
    >>> assert Payment('phone') is Payment.Phone
    >>> assert Payment(Payment.Phone) is Payment.Phone
    >>>
    >>> paid = Payment(adam_paid)
    >>> assert paid is adam_paid


As you can see, every variant constructs an instance of the same type ``Payment``,
and yet, every instance is identified with its own tag. You can use this tag to branch
your business logic, like in a function below:

.. code-block:: python

    def notify_restaurant_owner(channel: Broadcaster, payment: Payment):
        if isinstance(payment, Payment.JustThankYou):
            channel.push(f'A customer said Big Thank You!')
        else:  # Cash, Card, Phone instances have the `payment.amount` attribute
            channel.push(f'A customer left {payment.amount}!')


And, of course, you can use Sum Types in signatures of your serializable data:

.. code-block:: python

    from typing import NamedTuple, Sequence
    from typeit import type_constructor

    class Payments(NamedTuple):
        latest: Sequence[Payment]

    mk_payments, serialize_payments = type_constructor ^ Payments

    json_ready = serialize_payments(Payments(latest=[adam_paid, jane_paid, fred_paid]))
    payments = mk_payments(json_ready)


Flags
-----

``typeit.flags.NON_STRICT_PRIMITIVES`` -
disables strict checking of primitive types. With this flag, a type constructor for a structure
with a ``x: int`` attribute annotation would allow input values of ``x`` to be strings that could be parsed
as integer numbers. Without this flag, the type constructor will reject those values. The same rule is applicable
to combinations of floats, ints, and bools:

.. code-block:: python

    construct, deconstruct = type_constructor ^ int
    nonstrict_construct, nonstrict_deconstruct = type_constructor & NON_STRICT_PRIMITIVES ^ int

    construct('1')            # raises typeit.Error
    construct(1)              # OK
    nonstrict_construct('1')  # OK
    nonstrict_construct(1)    # OK


Extensions
----------

TODO

