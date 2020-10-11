Changing input_algorithms api
=============================

I built this https://delfick-project.readthedocs.io/en/latest/api/norms/index.html
many years ago which is based on the premise that if you have a value and a
``meta`` object, you can validate and normalise that value by saying
``spec.normalise(meta, val)`` and then the rest of the library is making it
easy to create that ``spec`` object.

This has served me well, but organic growth and decisions that have aged poorly
means the API I have created is less than ideal. So I want to fix that.

Currently, what I use the most is creating a ``FieldSpec`` on a ``dictobj.Spec``
class to turn a dictionary into an instance of a class:

.. code-block:: python

    from delfick_project.norm import dictobj, sb, Meta


    class special_spec(sb.Spec):
        def normalise(self, meta, val):
            return (val, 1)


    class FormattedThing(dictobj.Spec):
        fmt_string = dictobj.Field(format_into=sb.string_spec)


    class MyFormatterClass:
        """Does the special formatting stuff, that part no different"""


    class Thing(dictobj.Spec):
        thing = dictobj.Field(sb.integer_spec, wrapper=sb.required)
        other = dictobj.Field(sb.string_spec, wrapper=sb.optional_spec)
        blah = dictobj.NullableField(sb.listof(sb.string_spec()))
        special = dictobj.Field(special_spec)
        fmted = dictobj.Field(FormattedThing.FieldSpec(formatter=MyFormatterClass))

    meta = Meta({"hello": {"there": "you"}}, [])
    val = {"thing": 2, "blah": ["meh"], "fmted": "{hello.there}"}
    thing = Thing.FieldSpec().normalise(meta, val)

The new way would look like:

.. code-block:: python

    from delfick_project import nz


    class norm_special(nz.Norm):
        def normalise(self, meta, val):
            return (val, 1)


    class FormattedThing(nz.Container):
        fmt_string = nz.Field(format_into=nz.norm_string)


    class Thing(nz.Container):
        thing = nz.RequiredField(nz.norm_integer)
        other = nz.OptionalField(nz.norm_string)
        blah = nz.NullableField(nz.create(nz.norm_list_of, nz.norm_string))
        special = nz.Field(norm_special)
        fmted = nz.Field(FormattedThing)


    class MyFormatterClass:
        """Does the special formatting stuff, that part no different"""


    meta = nz.Meta({"hello": {"there": "you"}}, formatter=MyformatterClass)
    val = {"thing": 2, "blah": ["meh"], "fmted": "{hello.there}"}
    thing = nz.using(Thing).create(val, meta=meta)

``create`` would be an alias for ``nz.using(Thing).normalise(meta, val)`` so it
can be used as a normal "spec" in current way of doing things and is necessary
to avoid having ``SpecClass.FieldSpec().empty_normalise(**val)`` which exists to avoid
having to say ``SpecClass.FieldSpec().normalise(Meta.empty(), val)``

And by having ``create`` as a separate method name, I can have a separate
signature where it's much easier to say I don't care about having my own meta
object.

The other thing to note here is putting the formatter on meta, so it gets
propagated everywhere. Currently there isn't a way to do that and so for every
``dictobj.Spec`` that requires a formatter, I have to give it when I create the
``spec`` with ``FieldSpec``. In all code that uses this, I always give the same
formatter class.

Renaming fields
---------------

Currently with ``dictobj.Spec``, if I want the object I'm normalising to have a
different field name than the one on the class, I need to wrap it in it's own
``spec`` that does the renaming:

.. code-block:: python

    class Thing(dictobj.Spec):
        special = dictobj.Field(sb.integer_spec)


    class thing_spec(sb.Spec):
        def normalise(self, meta, val):
            val = sb.dictionary_spec().normalise(meta, val)
            if "special-value" not in val:
                raise BadSpecValue("Expected special-value in the value", meta=meta)
            return {"special": val["special-value"]}


    thing = thing_spec().normalise(Meta.empty(), {"special-value": 20})

The idea is to make this unnecessary. Either with this when it's just a rename:

.. code-block:: python

    class Thing(nz.Container):
        special = nz.Field(nz.norm_integer, renamed_key="special-value")


    thing = nz.using(Thing).create({"special-value": 20})

Or with some kind of transformer defined on the class:

.. code-block:: python

    class norm_transform_input(nz.Norm):
        def normalise(meta, val):
            return nz.norm_renamed_keys_dict(("special-value", "special")).normalise(meta, val)


    class Thing(nz.Container.Transformed(transform_input)):
        special = nz.Field(nz.norm_integer)


    thing = nz.using(Thing).create({"special-value": 20})

In both new ways, I don't have to care that when I normalise with this class I
first must transform the value.

Non dictionaries
----------------

The other problem with the ``FieldSpec`` thing is there isn't consistency when
I want to normalise a value that isn't a dictionary:

.. code-block:: python

    thing = sb.listof(sb.string_spec()).normalise(Meta.empty(), ["one", "two"])

But with new way I can use the ``nz.using(norm).create(val)``:

.. code-block:: python

    thing = nz.using(nz.create(nz.norm_list_of, sb.string_spec)).create(["one", "two"])

Creating a simple norm
----------------------

Currently if I want something with a normalise method that does essentially
nothing I have to create the entire class:

.. code-block:: python

    class simple_spec(sb.Spec):
        def normalise(meta, val):
            return hard_coded_value

I can make this better:

.. code-block:: python
        
    norm_simple = sb.from_func(lambda meta, val: return hard_coded_value)

    # or

    norm_simple = nz.hardcoded(hard_coded_value)

Different design decisions
--------------------------

I want to make it harder to create instances without normalising and I want to
make it harder to create class normalisers with invalid specifications.

So for the first one, currently if you have:

.. code-block:: python

    class Thing(dictobj.Spec):
        one = ...
        two = ...
        three = ...

You can say ``thing = Thing(one=1, two=3, three="asdf")`` and it'll bypass
whatever rules you had. I allowed this in the first place because the idea was
in tests you may not want that normalisation. However that essentially never
happens, and it makes it possible to not do that normalisation if you don't know
that you should.

Instead I'll make it raise an error if you try that and also ensure that doing a
``nz.using(Thing).create(val)`` returns an instance that allows
``isinstance(instance, Thing)`` to still return True.

The question becomes why don't I make ``__init__`` just do a create then? The
answer is a philosophy I have that says a class constructor should never raise
an exception or have side effects, which is exactly what the normalisation
process has. The idea of create is that it's an explicit act of transformation
before we pass in valid values into a class.

The second want, making sure I don't have invalid normalisers is to avoid this
problem:

.. code-block:: python

    class Thing(dictobj.Spec):
        one = dictobj.Field(sb.listof(sb.string_spec))

Here I've given ``listof`` a ``spec`` that isn't instantiated, and I won't know
that till runtime when I try to normalise it and it complains I gave the normalise
method ``meta, val`` rather than ``self, meta, val``. Super infuriating!

I fix this by making it consistent to provide a ``norm`` without instantiating it
so saying ``nz.create(sb.listof, sb.string_spec)`` which is essentially lisp
for ``sb.listof(sb.string_spec())``.

Extra fields on the class
-------------------------

Currently you have to say ``Thing.FieldSpec()`` because I want to limit what I
add to the class to make sure that you don't accidentally override machinery
that needs to exist. I hate this method name very much. I'll make it so the only
extra thing I add to the class is a ``instance.Meta`` which will hold all the
information on the original definition and a ``norm`` for creating an instance of
the class from a value that has instantiated as much as it can.

For this reason, you have to say ``nz.using(Thing).create`` instead of
``Thing.create``. But having the latter would be useful, so I'd have:

.. code-block:: python

    class Thing(nz.Container.WithCreate()):
       ...

    thing = Thing.create(val)

Consistent naming
-----------------

Currently I have a mix of ``sb.<name>_spec`` and ``sb.<name>`` for example,
``sb.integer_spec`` vs ``sb.required``. Also, people get confused by the word
``spec``, so I want to instead make a more consistent naming scheme of
``nz.norm_<name>`` for example ``nz.norm_integer`` and ``nz.norm_required``
and anything that does a transformation that isn't itself an ``nz.Norm`` object
can not have that prefix. For example ``nz.create``.

And I'd rename the current ones, and make the current names an alias to the new
implementation with a deprecation notice on use.

Removing dictobj
----------------

Currently I have the idea of the ``dictobj``. This is a dictionary that acts like
an object. I made it like that because of how I used to use them with a
``option_merge.MergedOptions`` object. I will instead change MergedOptions to
be able to access attributes on normal objects instead of just dictionaries.

Currently ``dictobj.Spec`` is a wrapper on an API that's a wrapper on ``dictobj``
itself.

So with ``dictobj`` you say:

.. code-block:: python

    class Thing(dictobj):
        fields = ["one", "two", "three"]

And then I made it so that ``fields`` property can have normalizers, and then
I made the ``Fields`` api to define that ``fields`` property using a meta class.

For performance reasons I want to make them normal objects that don't behave
like dictionaries at all. And instead implement a ``nz.as_dict(instance)``
that returns either the result of ``as_dict()``, or a dictionary
of the nz fields on the instance, or complain if it has neither of those.

Doing this will mean a few things:

* Don't add ``fields`` or ``as_dict`` property to the class that cannot be
  overridden
* Don't add dictionary methods to the class
* Simplify the creation of those objects
* Those objects don't need an inheritance chain from the start
* I don't have to do the ``dont_prefix=[dictobj]`` hack when I create a
  ``MergedOptions`` object.
* Don't create features in nz that exist only for option_merge

If I want an object like the above I can do:

.. code-block:: python

    class Thing(nz.Container.WithFields("one", "two", "three")):
        pass

BadSpecValue class
------------------

To remove all instances of the word Spec, I'll do the following:

.. code-block:: python

    class BadNorm(...):
        pass

    BadSpecValue = BadNorm

Also, I want to force having a meta in the kwargs so I'll make a new error to
raise with a slightly different signature:

.. code-block:: python

    class NormError(BadNorm):
        def __init__(self, msg="", *, meta, **kwargs):
            super().InvalidValue(msg, **kwargs)

And start using ``raise nz.NormError("nope", meta=meta)`` everywhere.

I can't just make ``BadNorm`` have this signature because I want
``except BadSpecValue`` to still catch these and I don't want existing code
using ``BadSpecValue`` to have this new restriction on ``__init__``.

Delayed looking at values
-------------------------

In the past I've needed to delay normalising a value and they way I did this
was returning a function that does that transformation:

.. code-block:: python

    class Thing(dictobj.Spec):
        stuff = dictobj.Field(sb.delayed(exensive_spec()))

    thing = Thing.FieldSpec().empty_normalise(stuff=value)
    stuff = thing.stuff() # does the expensive_spec.normalise(meta, val) at this point

I can do better and make a descriptor that does this on access:

.. code-block:: python

    class Thing(nz.Container):
        stuff = nz.DescriptorField(expensive_spec)

    thing = nz.using(Thing).create()
    stuff = thing.stuff # does the expensive_spec.normalise(meta, val) at this point

And while I'm at it, I can make descriptor fields that do transformations on
the transformed value:

.. code-block:: python

    class Descriptor(nz.Descriptor):
        def get_value(self, instance, current_value):
            """Not defining means it'll always just return current value"""
            return value_from_logic

        def set_value(self, instance, current_value, new_value):
            """Not defining means you can't set"""
            return value_to_replace_current_value

        def remove_value(self, instance, current_value):
            """Not defining means you can't delete"""
            do_something_with_current_value()

    class Thing(nz.Container):
        stuff = nz.Field(nz.norm_string, descriptor=Descriptor)

In this example, descriptor can be any normal python descriptor and using
``nz.Descriptor`` is optional, but removes some boilerplate you'd otherwise have
to implement.

The descriptor value may be combined with a ``nz.DescriptorField`` and will run
the values it receives through the norm with original meta object before your
descriptor gets the value.

Why nz?
-------

Using everything off ``nz\.`` makes it super easy to search for instances of
using this library, which means changes like this one in the future are even
easier to find in your codebase.

To ease mocking, nz will be a module that includes everything in an ``__all__``
so you can import things directly, but I'll highly discourage this::
    
    Namespaces are one honking great idea -- let's do more of those!

Also, ``nz`` is a two letter variable that is unlikely to happen naturally, so
it's easy/quick to type, and easy to search for.

It's short for ``normalize``. I'd use ``norm`` but that's too close to the
current ``delfick_project.norms`` module, and ``norm.norm_string`` is a stutter.
