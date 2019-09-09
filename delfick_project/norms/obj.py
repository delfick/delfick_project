"""
This is an object that behaves like both an object (dot notation access to
attributes) and like a dictionary (square bracket notation access to attrs).

It is a subclass of ``dict`` and has ``is_dict`` set to True.

It will also generate an ``__init__`` for you based on what you specify as the
``fields`` attribute.

.. code-block:: python

    class MyAmazingKls(dictobj):
        fields = ["one", "two", ("three", 4)]

Creates an ``__init__`` that behaves like:

.. code-block:: python

    def __init__(self, one, two, three=4):
        self.one = one
        self.two = two
        self.three = three

``fields``
    Must be an iterable of strings where each string is a valid variable name.

    Or a tuple of ``(<variable_name>, <dflt_value>)`` where the ``<dflt_value>``
    is used if that variable is not passed into ``__init__``.

    Because it must be an iterable, it can also be a dictionary where the values
    are docstrings for the attributes!

    .. code-block:: python

        class MyAmazingKls(dictobj):
            fields = {
                  "one": "The first argument"
                , "two": "The second argument"
                , ("three", 4): "Optional third argument"
                }

    Is a perfectly valid example.

    Note that if you specify fields as a dictionary, you must specify those
    arguments as keyword arguments when you instantiate the class.

Once an instance of ``dictobj`` is created you may access the attributes however
you wish!

.. code-block:: python

    instance = MyAmazingKls(one=1, two=2)

    instance.one == 1
    instance["one"] == 1

    instance.three == 4

    list(instance.items()) == [("one", 1), ("two", 2), ("three", 4)]

    instance.as_dict() == {"one": 1, "two": 2, "three": 4}
"""
from .field_spec import Field, NullableField
from . import spec_base as sb
from .errors import BadSpec

from collections import defaultdict

_cached_fields = {}


class Fields:
    @classmethod
    def make(kls, fieldskls, fields):
        if fieldskls not in _cached_fields:
            if not fields:
                _cached_fields[fieldskls] = None
            else:
                _cached_fields[fieldskls] = Fields(fieldskls, fields)
        return _cached_fields[fieldskls]

    def __init__(self, kls, fields):
        self.kls = kls
        self.posargs = []
        self.kwargs = []

        if isinstance(fields, (tuple, list)):
            result = self.posargs
        elif isinstance(fields, dict):
            result = self.kwargs
        else:
            raise TypeError(
                "Fields on kls {0} should be a list, tuple or dictionary, got {1}".format(
                    kls, type(fields)
                )
            )

        for i, field in enumerate(fields):
            if isinstance(field, str):
                result.append((field,))
            elif isinstance(field, tuple) and len(field) == 2 and isinstance(field[0], str):
                result.append(field)
            else:
                raise TypeError(
                    "Field {0} of kls {1} is not a valid field, got {2}".format(i, kls, field)
                )

        names = [f[0] for f in result]
        if len(set(names)) != len(names):
            by_name = defaultdict(int)
            for n in names:
                by_name[n] += 1
            duplicated = {n: num for n, num in by_name.items() if num > 1}
            raise TypeError(
                "Found duplicated fields in definition of {0}: {1}".format(
                    kls, sorted(duplicated.keys())
                )
            )

    def resolve(self, args, kwargs):
        if args and self.kwargs:
            raise TypeError("Expected only keyword arguments")

        if len(args) > len(self.posargs):
            raise TypeError(
                "Expected up to {0} positional arguments, got {1}".format(
                    len(self.posargs), len(args)
                )
            )

        result = {}
        pos = self.resolve_provided(result, args, kwargs)
        self.resolve_positional_dflts(result, pos)
        self.resolve_kwargs_dflts(result)
        return result

    @property
    def all_fields(self):
        yield from self.posargs
        yield from self.kwargs

    def resolve_provided(self, result, args, kwargs):
        pos = 0
        for value in args:
            item = self.posargs[pos]
            if len(item) == 2:
                name, _ = item
            else:
                (name,) = item
            result[name] = value
            pos += 1

        for field, value in kwargs.items():
            found = False
            for item in self.all_fields:
                if len(item) == 2:
                    name, _ = item
                else:
                    (name,) = item

                if name == field:
                    if name in result:
                        raise TypeError(
                            "Cannot provide a field ({0}) as both positional and keyword arguments".format(
                                name
                            )
                        )
                    result[field] = value
                    found = True

            if not found:
                raise TypeError(
                    "Received a keyword argument ({0}) that isn't on the class".format(field)
                )

        return pos

    def resolve_positional_dflts(self, result, pos):
        for i, item in enumerate(self.posargs[pos:]):
            if len(item) == 2:
                name, dflt = item
                if name not in result:
                    if callable(dflt):
                        dflt = dflt()
                    result[name] = dflt
            else:
                (name,) = item
                if name not in result:
                    raise TypeError(
                        "No default value set for positional argument {0} ({1}) and no value provided".format(
                            i + pos, name
                        )
                    )

    def resolve_kwargs_dflts(self, result):
        for item in self.kwargs:
            if len(item) == 2:
                name, dflt = item
                if name not in result:
                    if callable(dflt):
                        dflt = dflt()
                    result[name] = dflt
            else:
                (name,) = item
                if name not in result:
                    raise TypeError(
                        "No default value set for keyword argument ({0}) and no value provided".format(
                            name
                        )
                    )


class dictobj(dict):
    fields = None
    is_dict = True

    Field = Field
    NullableField = NullableField

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.setup(*args, **kwargs)

    @classmethod
    def __init_subclass__(kls, **kwargs):
        super().__init_subclass__(**kwargs)
        Fields.make(kls, kls.fields)

    def __bool__(self):
        """
        Dictionaries are Falsey when empty, whereas we want this to be Truthy
        like a normal object
        """
        return True

    def setup(self, *args, **kwargs):
        fields = Fields.make(self.__class__, self.fields)

        if fields is None:
            if args:
                raise TypeError("Expected 0 positional arguments, got {0}".format(len(args)))
            if kwargs:
                raise TypeError("Expected 0 keyword arguments, got {0}".format(len(kwargs)))
        else:
            for key, value in fields.resolve(args, kwargs).items():
                setattr(self, key, value)

    def __getattr__(self, key):
        """Pretend object access"""
        key = str(key)
        if key not in self or hasattr(self.__class__, key):
            return object.__getattribute__(self, key)

        try:
            return super().__getitem__(key)
        except KeyError as e:
            if e.message == key:
                raise AttributeError(key)
            else:
                raise

    def __getitem__(self, key):
        """
        If the key is on the class, then return that attribute, otherwise do a
        super call to ``dict.__getitem__``.
        """
        key = str(key)
        if key not in self and hasattr(self.__class__, key):
            return object.__getattribute__(self, key)
        else:
            return super().__getitem__(key)

    def __setattr__(self, key, val):
        """
        We use the setitem logic on the class.

        This will put the value in the underlying dictionary and if the key
        is a property on the instance, override that property on the instance.
        """
        self[key] = val

    def __delattr__(self, key):
        """
        If the key is on the class itself, then delete the attribute from the
        instance, otherwise do a super call to ``dict.__delitem__`` on this
        instance.
        """
        key = str(key)
        if key not in self or hasattr(self.__class__, key):
            object.__delattr__(self, key)
        else:
            del self[key]

    def __setitem__(self, key, val):
        """
        If the key is on the class itself, then set the value as an attribute on
        the class, otherwise, use a super call to ``dict.__setitem__`` on this
        instance.
        """
        if hasattr(self.__class__, key):
            object.__setattr__(self, key, val)
        super().__setitem__(key, val)

    def clone(self):
        """Return a clone of this object"""
        result = {}
        for field in self.fields:
            if isinstance(field, tuple):
                field = field[0]
            result[field] = self[field]

        return self.__class__(**result)

    def as_dict(self, **kwargs):
        """
        Return as a deeply nested dictionary

        This will call ``as_dict`` on values if they have such an attribute.
        """
        if not self.fields:
            return {}

        result = {}
        for field in self.fields:
            if isinstance(field, tuple):
                field = field[0]

            val = self[field]
            if hasattr(val, "as_dict"):
                result[field] = val.as_dict(**kwargs)
            else:
                result[field] = val

        return result

    @classmethod
    def selection(kls, kls_name, wanted, **kwargs):
        """
        Return a new dictobj() that only creates a new class with a selection of the fields

        We can also mark some fields as required, some as optional, or all as optional/required.

        For example:

        .. code-block:: python

            class Blah(dictobj.Spec):
                one = dictobj.Field(sb.string_spec())
                two = dictobj.Field(sb.string_spec())
                three = dictobj.Field(sb.string_spec())

            Meh = Blah.selection("Meh", ["one", "two"], all_optional=True)

            meh = Meh(one="1")
            assert meh.one == "1"
            assert meh.two is sb.NotSpecified
            assert not hasattr(meh, "three")

        keyword Options are as follows:

        optional
            list of keys to make optional

        required
            list of keys to make required

        all_required
            boolean saying to set all keys to required

        all_optional
            boolean saying to set all keys to optional

        This works by returning a new class with only some of the fields in the fields list

        .. note:: The keyword options only work for dictobj.Spec objects and are ignored for normal dictobj objects
        """
        fields = kls.fields
        name_map = {}
        any_spec = sb.any_spec()

        # Make a map of name of the field to the field itself
        # Fields may be either <name> or (<name>, <default>)
        for field in fields:
            field_name = field
            if type(field) is tuple:
                field_name = field_name[0]
            name_map[field_name] = field

        # Make sure we are selecting fields that exist
        missing = set(wanted) - set(name_map)
        if missing:
            raise BadSpec(
                "Tried to make a selection from keys that don't exist",
                missing=missing,
                available=list(name_map),
                wanted=wanted,
            )

        # The final result isn't inheriting from kls so that we can not inherit fields we don't want
        # But we still want everything else from kls to pretend it's inherited.......
        # I doubt this will work with super though..... feel free to raise an issue if this is undesirable...
        attrs = {}
        extra = set(dir(kls)) - set(dir(dictobj)) - set(name_map) - set(["FieldSpec"])
        attrs.update(dict((k, getattr(dictobj, k)) for k in extra))

        # Collect our new fields
        new_fields = {}
        for field_name, field in name_map.items():
            if field_name in wanted:
                if type(fields) is dict:
                    new_fields[field] = fields[field]
                else:
                    new_fields[field] = any_spec

        if not hasattr(kls, "FieldSpec"):
            # We weren't selecting from dictobj.Spec, so let's just set the fields and be done
            # Normal dictobj has no normalise functionality and so no point in setting such things
            attrs["fields"] = new_fields
            return type(kls_name, (dictobj,), attrs)

        # Ok, so, for dictobj.Spec, we set attrs on the class rather than fields
        # So let's seed the attrs with our cloned fields
        for name in name_map:
            if name in wanted:
                attrs[name] = getattr(kls, name)
                if getattr(attrs[name], "is_dictobj_field", False):
                    attrs[name] = attrs[name].clone()

        def wrap(spec, wrapper):
            """Helper to wrap a spec with some wrapper"""
            h = None
            s = spec

            # A spec can be <options> or (<help string, <options>)
            if type(s) is tuple:
                h, s = spec

            if callable(s):
                s = lambda: wrapper(s())
            else:
                if getattr(s, "is_dictobj_field", False):
                    # We don't want to override the default with optional_spec
                    if wrapper is sb.optional_spec and s.default is not sb.NotSpecified:
                        s = s.clone()
                    else:
                        # We also don't want to override an existing wrapper
                        if s.wrapper is not sb.NotSpecified:
                            s = s.clone(wrapper=lambda spec: wrapper(s.wrapper(spec)))
                        else:
                            s = s.clone(wrapper=wrapper)
                else:
                    s = lambda: wrapper(s or any_spec)

            return s

        def all_wrap(key, wrapper):
            """helper for wrapping all fields"""
            if kwargs.get(key):
                for field, val in new_fields.items():
                    attrs[field] = wrap(val, wrapper)

        def specific_wrap(key, wrapper):
            """Helper for wrapping specific keys"""
            missing = []
            for field_name in kwargs.get(key, []):
                field = name_map[field_name]
                if field in new_fields:
                    attrs[field] = wrap(new_fields[field], wrapper)
                else:
                    missing.append(field_name)
            if missing:
                raise BadSpec(
                    "Tried to wrap keys that didn't exist",
                    wrap_as=key,
                    missing=missing,
                    available=list(name_map),
                    wanted=kwargs.get(key),
                )

        # Ok, now we use our wrap helper for optional settings
        all_wrap("all_optional", sb.optional_spec)

        # Required is used to override all_optional
        specific_wrap("required", sb.required)

        # Set all things to required if so desired
        all_wrap("all_required", sb.required)

        # And override all_required with optional
        specific_wrap("optional", sb.optional_spec)

        # Finally, we return our new class!
        return type(kls_name, (dictobj.Spec,), attrs)


class Spec(dictobj, metaclass=Field.metaclass):
    pass


dictobj.Spec = Spec
