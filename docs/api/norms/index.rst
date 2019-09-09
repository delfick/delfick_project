.. _norms:

Data Validation and normalisation
=================================

The ``delfick_project.norms`` package provides helpers for validating and
normalising data.

Everything boils down to objects that have a ``normalise(meta, val)`` method
that takes in a ``meta`` object describing the root of our data and where in the
data we are, and the ``val`` which is the current value to validate and normalise.

Normalisation is where we take the data and modify it to meet the shape we
want.

An example of this is:

.. code-block:: python

   from delfick_project.norms import sb, Meta, BadSpecValue

   spec = sb.listof(sb.string_spec())
   normalised = spec.normalise(Meta.empty(), "a_string")
   assert normalised == ["a_string"]

   normalised = spec.normalise(Meta.empty(), ["one", "two"])
   assert normalised == ["one", "two"]
   
   with assertRaises(BadSpecValue, "Expected a string", got=bool, meta=meta.indexed_at(0)):  
      spec.normalise(Meta.empty(), True)

Included in this package is a class for creating objects from dictionaries of
data and validation objects that allow you to declare styles of validation on
your data.

.. toctree::

    api/spec_base
    api/validators
    api/meta
    api/dictobj
    api/errors
