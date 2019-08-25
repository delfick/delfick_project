"""
spec_base is the core of the norm package and implements many specification
classes based off the ``Spec`` class.

A specification is an object with a ``normalise`` method and is used to validate
and transform data.
"""
from .errors import BadSpec, BadSpecValue, BadDirectory, BadFilename

import operator
import io
import os

default_specs = []

def spec(func):
    """For the documentationz!"""
    default_specs.append((func.__name__, func))
    return func

class NotSpecified(object):
    """Tell the difference between None and not specified"""

    _merged_options_formattable = True

    def __repr__(self):
        return "<NotSpecified>"

    def __str__(self):
        return "<NotSpecified>"

def apply_validators(meta, val, validators, chain_value=True):
    """
    Apply a number of validators to a value.

    chain_value
        Sets whether to pass the validated value into the next
        validator or whether to use the original value each time

    All validators are tried and errors are collected.

    If any fails, an error is raised, otherwise the value is returned.

    Where value is the original value, or the result of the last validator
    depending on ``chain_value``.
    """
    errors = []
    for validator in validators:
        try:
            nxt = validator.normalise(meta, val)
            if chain_value:
                val = nxt
        except BadSpecValue as e:
            errors.append(e)

    if errors:
        raise BadSpecValue("Failed to validate", meta=meta, _errors=errors)

    return val

class Spec(object):
    """
    Default shape for a spec (specification, not test!)

    __init__
        passes all *args and **kwargs to a ``self.setup`` if that exists on the
        class

    normalise
        Calls one of the following functions on the class, choosing in this order:

        normalise_either
            If defined, then this is meant to work with both a specified value as
            well as ``NotSpecified``.

            If this function returns ``NotSpecified``, then we continue looking
            for a function to handle this value.

        normalise_empty
            Called if the value is ``NotSpecified``.

        default
            Called if the value is ``NotSpecified``.

        return NotSpecified
            If the value is NotSpecified and the above don't return, then the
            value is returned as is.

        normalise_filled
            The value is not ``NotSpecified``

        If none of those options are defined, then an error is raised complaining
        that we couldn't work out what to do with the value.

        Note that any validation errors should be an subclass of
        ``delfick_project.norms.BadSpec``. This is because the default specs
        only catch such exceptions. Anything else is assumed to be a
        ProgrammerError and worthy of a traceback.

    fake_filled
        If ``fake`` is on the class that is used, otherwise if ``default`` is on
        the class that is used, otherwise we return ``NotSpecified``.

        This is used to generate fake data from a specification.

    The idea is that a Spec is an object with a ``normalise`` method that takes
    in two objects: ``meta`` and ``val``.

    ``meta``
        Should be an instance of ``delfick_project.norms.Meta`` and is used to
        indicate where we are. This should be passed to any children specifications.

        For example, if we are normalising a dictionary where a child specification
        is used on a particular value at a key called ``a_key``, we should do
        something similar to:

        .. code-block:: python

            child_spec().normalise(meta.at("a_key"), val["a_key"])

    ``val``
        Should be the value we are normalising. The normalising process should
        validate and transform the value to be what we are specifying.

        For example listof(string_spec()) will transform a single string to be
        a list of one string.

    When you create a subclass of ``Spec`` you either implement one of the
    ``normalise_*`` methods or ``normalise`` itself.
    """
    def __init__(self, *pargs, **kwargs):
        self.pargs = pargs
        self.kwargs = kwargs
        if hasattr(self, "setup"):
            self.setup(*pargs, **kwargs)

    def normalise(self, meta, val):
        """Use this spec to normalise our value"""
        if hasattr(self, "normalise_either"):
            result = self.normalise_either(meta, val)
            if result is not NotSpecified:
                return result

        if val is NotSpecified:
            if hasattr(self, "normalise_empty"):
                return self.normalise_empty(meta)
            elif hasattr(self, "default"):
                return self.default(meta)
            else:
                return val
        elif hasattr(self, "normalise_filled"):
            return self.normalise_filled(meta, val)

        raise BadSpec("Spec doesn't know how to deal with this value", spec=self, meta=meta, val=val)

    def fake_filled(self, meta, with_non_defaulted=False):
        """Return this spec as if it was filled with the defaults"""
        if hasattr(self, "fake"):
            return self.fake(meta, with_non_defaulted=with_non_defaulted)
        if hasattr(self, "default"):
            return self.default(meta)
        return NotSpecified

@spec
class pass_through_spec(Spec):
    """
    Usage
        .. code-block:: python

            pass_through_spec().normalise(meta, val)

    Will not touch the value in any way and just return it.
    """
    def normalise_either(self, meta, val):
        return val

@spec
class always_same_spec(Spec):
    """
    Usage
        .. code-block:: python

            always_same_spec(result).normalise(meta, val)

    Will ignore value and just return ``result``.
    """
    def setup(self, result):
        self.result = result

    def normalise_either(self, meta, val):
        return self.result

@spec
class dictionary_spec(Spec):
    """
    Usage
        .. code-block:: python

            dictionary_spec().normalise(meta, val)

    Will normalise ``NotSpecified`` into ``{}``

    Specified values are valid if
    ``type(val) is dict`` or ``val.is_dict() is True``. If either those
    conditions are true, then the dictionary is returned as is.
    """
    def default(self, meta):
        return {}

    def normalise_filled(self, meta, val):
        """Make sure it's a dictionary"""
        if not isinstance(val, dict) and not getattr(val, "is_dict", False):
            raise BadSpecValue("Expected a dictionary", meta=meta, got=type(val))

        return val

@spec
class dictof(dictionary_spec):
    """
    Usage
        .. code-block:: python

            dictof(name_spec, value_spec).normalise(meta, val)

            # or

            dictof(name_spec, value_spec, nested=True).normalise(meta, val)

    This will first use ``dictionary_spec`` logic on the value to ensure we are
    normalising a dictionary.

    It will then use ``name_spec`` and ``value_spec`` on the items in the value
    to produce a resulting dictionary.

    For example if we have ``{"a": 1, "b": 2}``, using dictof is equivalent to:

    .. code-block:: python

        { name_spec.normalise(meta.at("a"), "a"): value_spec.normalise(meta.at("a"), 1)
        , name_spec.normalise(meta.at("b"), "b"): value_spec.normalise(meta.at("b"), 2)
        }

    This specification will also do the same to any ``dictionary`` values it has
    if ``nested`` is set to ``True`` (defaults to ``False``)

    It will also collect any errors and raise a collection of all errors it
    comes across.
    """
    def setup(self, name_spec, value_spec, nested=False):
        self.nested = nested
        self.name_spec = name_spec
        self.value_spec = value_spec

    def normalise_filled(self, meta, val):
        """Make sure all the names match the spec and normalise the values"""
        val = super(dictof, self).normalise_filled(meta, val)

        result = {}
        errors = []
        for key, value in val.items():
            try:
                name = self.name_spec.normalise(meta.at(key), key)
            except BadSpec as error:
                errors.append(error)
            else:
                try:
                    if self.nested and (isinstance(value, dict) or getattr(value, "is_dict", False)):
                        normalised = self.__class__(self.name_spec, self.value_spec, nested=self.nested).normalise(meta.at(key), value)
                    else:
                        normalised = self.value_spec.normalise(meta.at(key), value)
                except BadSpec as error:
                    errors.append(error)
                else:
                    result[name] = normalised

        if errors:
            raise BadSpecValue(meta=meta, _errors=errors)

        return result

@spec
class tupleof(Spec):
    """
    Usage
        .. code-block:: python

            tupleof(spec).normalise(meta, val)

    This specification will transform ``NotSpecified`` into ``()``

    If we don't have a tuple, we turn the value into a tuple of that value.
    Except for lists which are turned in a tuple.

    The resulting tuple of items is returned.
    """
    def setup(self, spec):
        self.spec = spec

    def default(self, meta):
        return ()

    def normalise_filled(self, meta, val):
        """Turn this into a tuple of it's not and normalise all the items in the tuple"""
        if not isinstance(val, list) and not isinstance(val, tuple):
            val = [val]

        result = []
        errors = []
        for index, item in enumerate(val):
            try:
                result.append(self.spec.normalise(meta.indexed_at(index), item))
            except BadSpec as error:
                errors.append(error)

        if errors:
            raise BadSpecValue(meta=meta, _errors=errors)

        return tuple(result)

@spec
class listof(Spec):
    """
    Usage
        .. code-block:: python

            listof(spec).normalise(meta, val)

            # or

            listof(spec, expect=typ).normalise(meta, val)

    This specification will transform ``NotSpecified`` into ``[]``

    If we don't have a list, we turn the value into a list of that value.

    If ``expect`` is specified, any item already passing ``isinstance(item, expect)``
    is left alone, otherwise ``spec`` is used to normalise the value.

    The resulting list of items is returned.
    """
    def setup(self, spec, expect=NotSpecified):
        self.spec = spec
        self.expect = expect

    def default(self, meta):
        return []

    def normalise_filled(self, meta, val):
        """Turn this into a list of it's not and normalise all the items in the list"""
        if self.expect is not NotSpecified and isinstance(val, self.expect):
            return [val]

        if not isinstance(val, list):
            val = [val]

        result = []
        errors = []
        for index, item in enumerate(val):
            if isinstance(item, self.expect):
                result.append((index, item))
            else:
                try:
                    result.append((index, self.spec.normalise(meta.indexed_at(index), item)))
                except BadSpec as error:
                    errors.append(error)

        if self.expect is not NotSpecified:
            for index, value in result:
                if not isinstance(value, self.expect):
                    errors.append(BadSpecValue("Expected normaliser to create a specific object", expected=self.expect, meta=meta.indexed_at(index), got=value))

        if errors:
            raise BadSpecValue(meta=meta, _errors=errors)

        return list(map(operator.itemgetter(1), result))

@spec
class set_options(Spec):
    """
    Usage
        .. code-block:: python

            set_options(<key1>=<spec1>, ..., <keyn>=<specn>).normalise(meta, val)

            # For example

            set_options(key_1=integer_spec(), key_2=string_spec()).normalise(meta, val)

    This specification transforms ``NotSpecified`` into ``{}``.

    Specified values are validated using ``dictionary_spec`` and then for each
    keyword argument we use either that key in the ``val`` or ``Notspecified``
    and normalise it with the ``spec`` for that key.

    Finally, we assemble the result from all these keys in a dictionary and
    return that.

    Errors are collected and raised in a group.

    Extra keys in ``val`` are ignored.
    """
    def setup(self, **options):
        self.options = options

    def default(self, meta):
        return {}

    def normalise_filled(self, meta, val):
        """Fill out a dictionary with what we want as well as the remaining extra"""
        # Make sure val is a dictionary!
        val = dictionary_spec().normalise(meta, val)

        result = {}
        errors = []

        for key, spec in self.options.items():
            nxt = val.get(key, NotSpecified)

            try:
                normalised = spec.normalise(meta.at(key), nxt)
                result[key] = normalised
            except (BadSpec, BadSpecValue) as error:
                errors.append(error)

        if errors:
            raise BadSpecValue(meta=meta, _errors=errors)

        return result

    def fake(self, meta, with_non_defaulted=False):
        """Return a dict with the defaults from the keys that have them"""
        result = {}
        for key, spec in self.options.items():
            fake = spec.fake_filled(meta, with_non_defaulted=with_non_defaulted)
            if fake is not NotSpecified or with_non_defaulted:
                result[key] = fake
        return result

@spec
class defaulted(Spec):
    """
    Usage
        .. code-block:: python

            defaulted(spec, dflt).normalise(meta, val)

    This specification will return ``dflt`` if ``val`` is ``NotSpecified``.

    Otherwise, it merely proxies ``spec`` and does ``spec.normalise(meta, val)``
    """
    def setup(self, spec, dflt):
        self.spec = spec
        self.default = lambda m: dflt

    def normalise_filled(self, meta, val):
        """Proxy our spec"""
        return self.spec.normalise(meta, val)

@spec
class required(Spec):
    """
    Usage
        .. code-block:: python

            required(spec).normalise(meta, val)

    This specification will raise an error if ``val`` is ``NotSpecified``.

    Otherwise, it merely proxies ``spec`` and does ``spec.normalise(meta, val)``
    """
    def setup(self, spec):
        self.spec = spec

    def normalise_empty(self, meta):
        """Complain that we have no value"""
        raise BadSpecValue("Expected a value but got none", meta=meta)

    def normalise_filled(self, meta, val):
        """Proxy our spec"""
        return self.spec.normalise(meta, val)

    def fake(self, meta, with_non_defaulted=False):
        return self.spec.fake_filled(meta, with_non_defaulted=with_non_defaulted)

@spec
class boolean(Spec):
    """
    Usage
        .. code-block:: python

            boolean().normalise(meta, val)

    This complains if the value is not ``isintance(val, bool)``.

    Otherwise it just returns the ``val``.

    .. note:: This specification does not handle ``NotSpecified``. This is a
        deliberate decision. Use defaulted(boolean(), <dflt>) if you want to
        handle that.
    """
    def normalise_filled(self, meta, val):
        """Complain if not already a boolean"""
        if not isinstance(val, bool):
            raise BadSpecValue("Expected a boolean", meta=meta, got=type(val))
        else:
            return val

@spec
class directory_spec(Spec):
    """
    Usage
        .. code-block:: python

            directory_spec().normalise(meta, val)

            # or

            directory_spec(spec).normalise(meta, val)

    This specification will first normalise ``val`` with ``spec`` if ``spec``
    is specified.

    It then makes sure that ``val`` is a string, exists, and is a directory.

    If it isn't, an error is raised, otherwise the ``val`` is returned.
    """
    def setup(self, spec=NotSpecified):
        self.spec = spec
        if self.spec is NotSpecified:
            self.spec = string_spec()

    def fake(self, meta, with_non_defaulted=False):
        return self.spec.fake_filled(meta, with_non_defaulted=with_non_defaulted)

    def normalise_either(self, meta, val):
        """Complain if not a meta to a directory"""
        if self.spec is not NotSpecified:
            val = self.spec.normalise(meta, val)

        if not isinstance(val, str):
            raise BadDirectory("Didn't even get a string", meta=meta, got=type(val))
        elif not os.path.exists(val):
            raise BadDirectory("Got something that didn't exist", meta=meta, directory=val)
        elif not os.path.isdir(val):
            raise BadDirectory("Got something that exists but isn't a directory", meta=meta, directory=val)
        else:
            return val

@spec
class filename_spec(Spec):
    """
    Usage
        .. code-block:: python

            directory_spec().normalise(meta, val)

            # or

            filename_spec(spec).normalise(meta, val)

    This specification will first normalise ``val`` with ``spec`` if ``spec``
    is specified.

    It then makes sure that ``val`` is a string, exists, and is a file.

    If it isn't, an error is raised, otherwise the ``val`` is returned.
    """
    def setup(self, spec=NotSpecified, may_not_exist=False):
        self.spec = spec
        self.may_not_exist = may_not_exist

    def normalise_filled(self, meta, val):
        if self.spec is not NotSpecified:
            val = self.spec.normalise(meta, val)

        if not isinstance(val, str):
            raise BadFilename("Didn't even get a string", meta=meta, got=type(val))

        if not os.path.exists(val):
            if self.may_not_exist:
                return val

            raise BadFilename("Got something that didn't exist", meta=meta, filename=val)

        if not os.path.isfile(val):
            raise BadFilename("Got something that exists but isn't a file", meta=meta, filename=val)

        return val

@spec
class file_spec(Spec):
    """
    Usage
        .. code-block:: python

            file_spec().normalise(meta, val)

    This will complain if ``val`` is not a file object, otherwise it just
    returns ``val``.
    """
    def normalise_filled(self, meta, val):
        """Complain if not a file object"""
        bad = False
        if not isinstance(val, io.TextIOBase):
            bad = True

        if bad:
            raise BadSpecValue("Didn't get a file object", meta=meta, got=val)

        return val

@spec
class string_spec(Spec):
    """
    Usage
        .. code-block:: python

            string_spec().normalise(meta, val)

    This transforms ``NotSpecified`` into ``""``

    If ``val`` is specified, it will complain if not ``isinstance(val, str)``
    , otherwise it just returns ``val``.
    """
    def default(self, meta):
        return ""

    def normalise_filled(self, meta, val):
        """Make sure it's a string"""
        if not isinstance(val, str):
            raise BadSpecValue("Expected a string", meta=meta, got=type(val))

        return val

@spec
class integer_spec(Spec):
    """
    Usage
        .. code-block:: python

            integer_spec().normalise(meta, val)

    This will complain if ``val`` is not an integer, unless it has ``isdigit``
    and this function returns ``True``.

    We return ``int(val)`` regardless.

    .. note:: This specification does not handle ``NotSpecified``. This is a
        deliberate decision. Use defaulted(integer_spec(), <dflt>) if you want
        to handle that.
    """
    def normalise_filled(self, meta, val):
        """Make sure it's an integer and convert into one if it's a string"""
        if not isinstance(val, bool) and (isinstance(val, int) or hasattr(val, "isdigit") and val.isdigit()):
            try:
                return int(val)
            except (TypeError, ValueError) as error:
                raise BadSpecValue("Couldn't transform value into an integer", meta=meta, error=str(error))
        raise BadSpecValue("Expected an integer", meta=meta, got=type(val))

@spec
class float_spec(Spec):
    """
    Usage
        .. code-block:: python

            float_spec().normalise(meta, val)

    If the ``val`` is not a ``bool`` then we do ``float(val)`` and return the
    result.

    Otherwise, or if that fails, an error is raised.
    """
    def normalise_filled(self, meta, val):
        """Make sure it's a float"""
        try:
            if not isinstance(val, bool):
                return float(val)
            else:
                raise BadSpecValue("Expected a float", meta=meta, got=bool)
        except (TypeError, ValueError) as error:
            raise BadSpecValue("Expected a float", meta=meta, got=type(val), error=error)

@spec
class string_or_int_as_string_spec(Spec):
    """
    Usage
        .. code-block:: python

            string_or_int_as_string_spec().normalise(meta, val)

    This transforms ``NotSpecified`` into ``""``

    If the ``val`` is not an integer or string, it will complain, otherwise it
    returns ``str(val)``.
    """
    def default(self, meta):
        return ""

    def normalise_filled(self, meta, val):
        """Make sure it's a string or integer"""
        if isinstance(val, bool) or (not isinstance(val, str) and not isinstance(val, int)):
            raise BadSpecValue("Expected a string or integer", meta=meta, got=type(val))
        return str(val)

@spec
class valid_string_spec(string_spec):
    """
    Usage
        .. code-block:: python

            valid_string_spec(validator1, ..., validatorn).normalise(meta, val)

    This takes in a number of validator specifications and applies them to ``val``
    after passing through ``valid_string_spec`` logic.

    Validators are just objects with ``normalise`` methods that happen to raise
    errors and return the ``val`` as is.

    If none of the validators raise an error, the original ``val`` is returned.
    """
    def setup(self, *validators):
        self.validators = validators

    def normalise_filled(self, meta, val):
        """Make sure if there is a value, that it is valid"""
        val = super(valid_string_spec, self).normalise_filled(meta, val)
        return apply_validators(meta, val, self.validators)

@spec
class integer_choice_spec(integer_spec):
    """
    Usage
        .. code-block:: python

            integer_choice_spec([1, 2, 3]).normalise(meta, val)

            # or

            integer_choice_spec([1, 2, 3], reason="Choose one of the first three numbers!").normalise(meta, val)

    This absurdly specific specification will make sure ``val`` is an integer
    before making sure it's one of the ``choices`` that are provided.

    It defaults to complaining ``Expected one of the available choices`` unless
    you provide ``reason``, which it will use instead if it doesn't match one
    of the choices.
    """
    def setup(self, choices, reason=NotSpecified):
        self.choices = choices
        self.reason = reason
        if self.reason is NotSpecified:
            self.reason = "Expected one of the available choices"

    def normalise_filled(self, meta, val):
        """Complain if val isn't one of the available"""
        val = super(integer_choice_spec, self).normalise_filled(meta, val)

        if val not in self.choices:
            raise BadSpecValue(self.reason, available=self.choices, got=val, meta=meta)

        return val

@spec
class string_choice_spec(string_spec):
    """
    Usage
        .. code-block:: python

            string_choice_spec(["a", "b", "c"]).normalise(meta, val)

            # or

            string_choice_spec(["a", "b", "c"], reason="Choose one of the first three characters in the alphabet!").normalise(meta, val)

    This absurdly specific specification will make sure ``val`` is a string
    before making sure it's one of the ``choices`` that are provided.

    It defaults to complaining ``Expected one of the available choices`` unless
    you provide ``reason``, which it will use instead if it doesn't match one
    of the choices.
    """
    def setup(self, choices, reason=NotSpecified):
        self.choices = choices
        self.reason = reason
        if self.reason is NotSpecified:
            self.reason = "Expected one of the available choices"

    def normalise_filled(self, meta, val):
        """Complain if val isn't one of the available"""
        val = super(string_choice_spec, self).normalise_filled(meta, val)

        if val not in self.choices:
            raise BadSpecValue(self.reason, available=self.choices, got=val, meta=meta)

        return val

@spec
class create_spec(Spec):
    """
    Usage
        .. code-block:: python

            create_spec(
                kls
                , validator1, ..., validatorn
                , key1=spec1, ..., keyn=specn
                ).normalise(meta, val)

    This specification will return ``val`` as is if it's already an instance of
    ``kls``.

    Otherwise, it will run ``val`` through all the ``validator``s before using
    the ``key``->``spec`` keyword arguments in a ``set_options`` specification
    to create the arguments used to instantiate an instance of ``kls``.
    """
    def setup(self, kls, *validators, **expected):
        self.kls = kls
        self.expected = expected
        self.validators = validators
        self.expected_spec = set_options(**expected)

    def default(self, meta):
        return self.kls(**self.expected_spec.normalise(meta, {}))

    def fake(self, meta, with_non_defaulted=False):
        return self.kls(**self.expected_spec.fake_filled(meta, with_non_defaulted=with_non_defaulted))

    def normalise_filled(self, meta, val):
        """If val is already our expected kls, return it, otherwise instantiate it"""
        if isinstance(val, self.kls):
            return val

        apply_validators(meta, val, self.validators, chain_value=False)
        values = self.expected_spec.normalise(meta, val)
        result = getattr(meta, 'base', {})
        for key in self.expected:
            result[key] = None
            result[key] = values.get(key, NotSpecified)
        return self.kls(**result)

@spec
class or_spec(Spec):
    """
    Usage
        .. code-block:: python

            or_spec(spec1, ..., specn).normalise(meta, val)

    This will keep trying ``spec.normalise(meta, val)`` until it finds one that
    doesn't raise a ``BadSpec`` error.

    If it can't find one, then it raises all the errors as a group.
    """
    def setup(self, *specs):
        self.specs = specs

    def normalise_filled(self, meta, val):
        """Try all the specs till one doesn't raise a BadSpec"""
        errors = []
        for spec in self.specs:
            try:
                return spec.normalise(meta, val)
            except BadSpec as error:
                errors.append(error)

        # If made it this far, none of the specs passed :(
        raise BadSpecValue("Value doesn't match any of the options", meta=meta, val=val, _errors=errors)

@spec
class match_spec(Spec):
    """
    Usage
        .. code-block:: python

            match_spec((typ1, spec1), ..., (typn, specn)).normalise(meta, val)

            # or

            match_spec((typ1, spec1), ..., (typn, specn), fallback=fspec).normalise(meta, val)

    This will find the ``spec`` associated with the first ``typ`` that succeeds
    ``isinstance(val, typ)``.

    .. note:: If ``spec`` is callable, we do ``spec().normalise(meta, val)``.

    If fallback is specified and none of the ``typ``s match the ``val`` then
    ``fpsec`` is used as the ``spec``. It is also called first if it's a
    callable object.

    If we can't find a match for the ``val``, an error is raised.
    """
    def setup(self, *specs, **kwargs):
        self.specs = specs
        self.fallback = kwargs.get("fallback")

    def normalise_filled(self, meta, val):
        """Try the specs given the type of val"""
        for expected_typ, spec in self.specs:
            if isinstance(val, expected_typ):
                if callable(spec):
                    spec = spec()
                return spec.normalise(meta, val)

        if self.fallback is not None:
            fallback = self.fallback
            if callable(self.fallback):
                fallback = self.fallback()
            return fallback.normalise(meta, val)

        # If made it this far, none of the specs matched
        raise BadSpecValue("Value doesn't match any of the options", meta=meta, got=type(val), expected=[expected_typ for expected_typ, _ in self.specs])

@spec
class and_spec(Spec):
    """
    Usage
        .. code-block:: python

            and_spec(spec1, ..., specn).normalise(meta, val)

    This will do ``val = spec.normalise(meta, val)`` for each ``spec`` that is
    provided and returns the final ``val``.

    If any of the ``spec``s fail, then an error is raised.
    """
    def setup(self, *specs):
        self.specs = specs

    def normalise_filled(self, meta, val):
        """Try all the specs"""
        errors = []
        transformations = [val]
        for spec in self.specs:
            try:
                val = spec.normalise(meta, val)
                transformations.append(val)
            except BadSpec as error:
                errors.append(error)
                break

        if errors:
            raise BadSpecValue("Value didn't match one of the options", meta=meta, transformations=transformations, _errors=errors)
        else:
            return val

@spec
class optional_spec(Spec):
    """
    Usage
        .. code-block:: python

            optional_spec(spec).normalise(meta, val)

    This will return ``NotSpecified`` if the ``val`` is ``NotSpecified``.

    Otherwise it merely acts as a proxy for ``spec``.
    """
    def setup(self, spec):
        self.spec = spec

    def fake(self, meta, with_non_defaulted=False):
        return self.spec.fake_filled(meta, with_non_defaulted=with_non_defaulted)

    def normalise_empty(self, meta):
        """Just return NotSpecified"""
        return NotSpecified

    def normalise_filled(self, meta, val):
        """Proxy the spec"""
        return self.spec.normalise(meta, val)

@spec
class dict_from_bool_spec(Spec):
    """
    Usage
        .. code-block:: python

            dict_from_bool_spec(dict_maker, spec).normalise(meta, val)

    If ``val`` is ``NotSpecified`` then we do ``spec.normalise(meta, {})``

    If ``val`` is a boolean, we first do ``val = dict_maker(meta, val)`` and
    then do ``spec.normalise(meta, val)`` to return the value.

    Example:

        A good example is setting enabled on a dictionary:

        .. code-block:: python

            spec = dict_from_bool_spec(lambda b: {"enabled": b}, set_options(enabled=boolean()))

            spec.normalise(meta, False) == {"enabled": False}

            spec.normalise(meta, {"enabled": True}) == {"enabled": True}
    """
    def setup(self, dict_maker, spec):
        self.spec = spec
        self.dict_maker = dict_maker

    def normalise_empty(self, meta):
        """Use an empty dict with the spec if not specified"""
        return self.normalise_filled(meta, {})

    def fake(self, meta, with_non_defaulted=False):
        return self.spec.fake_filled(meta, with_non_defaulted=with_non_defaulted)

    def normalise_filled(self, meta, val):
        """Proxy the spec"""
        if isinstance(val, bool):
            val = self.dict_maker(meta, val)
        return self.spec.normalise(meta, val)

@spec
class formatted(Spec):
    """
    Usage
        .. code-block:: python

            formatted(spec, formatter).normalise(meta, val)

            # or

            formatted(spec, formatter, expected_type=typ).normalise(meta, val)

            # or

            formatted(spec, formatter, after_format=some_spec()).normlise(meta, val)

    This specification is a bit special and is designed to be used with
    ``MergedOptionStringFormatter`` from the ``option_merge`` library
    (http://option-merge.readthedocs.org/en/latest/docs/api/formatter.html).

    The idea is that ``meta.everything`` is an instance of ``MergedOptions`` and
    it will create a new instance of ``meta.everything.__class__`` using
    ``meta.everything.converters`` and ``meta.everything.dont_prefix`` if they
    exist. Note that this should work with normal dictionaries as well.

    We then update our copy of ``meta.everything`` with ``meta.key_names()`` and
    create an instance of ``formatter`` using this copy of the ``meta.everything``
    , ``meta.path`` and ``spec.normalise(meta, val)`` as the value.

    We call ``format`` on the ``formatter`` instance, check that it's an instance
    of ``expected_type`` if that has been specified.

    Once we have our formatted value, we normalise it with after_format if that was
    specified.

    And finally, return a value!
    """
    def setup(self, spec, formatter, expected_type=NotSpecified, after_format=NotSpecified):
        self.spec = spec
        self.formatter = formatter
        self.after_format = after_format
        self.expected_type = expected_type
        self.has_expected_type = self.expected_type and self.expected_type is not NotSpecified

    def fake(self, meta, with_non_defaulted=False):
        if with_non_defaulted:
            return self.normalise_either(meta, NotSpecified)
        else:
            return NotSpecified

    def normalise_either(self, meta, val):
        """Format the value"""
        options_opts = {}
        if hasattr(meta.everything, "converters"):
            options_opts['converters'] = meta.everything.converters
        if hasattr(meta.everything, "dont_prefix"):
            options_opts["dont_prefix"] = meta.everything.dont_prefix
        options = meta.everything.__class__(**options_opts)
        options.update(meta.key_names())
        options.update(meta.everything)

        af = self.after_format
        if af != NotSpecified:
            af = self.after_format
            if callable(af):
                af = af()

        specd = self.spec.normalise(meta, val)
        if not isinstance(specd, str) and af != NotSpecified:
            return af.normalise(meta, specd)

        formatted = self.formatter(options, meta.path, value=specd).format()
        if af != NotSpecified:
            formatted = af.normalise(meta, formatted)

        if self.has_expected_type:
            if not isinstance(formatted, self.expected_type):
                raise BadSpecValue("Expected a different type", got=type(formatted), expected=self.expected_type)

        return formatted

@spec
class many_format(Spec):
    """
    Usage
        .. code-block:: python

            many_format(spec, formatter).normalise(meta, val)

            # or

            many_format(spec, formatter, expected_type=typ).normalise(meta, val)

    This is a fun specification!

    It essentially does ``formatted(spec, formatter, expected_type=typ).normalise(meta, val)``
    until the result doesn't change anymore.

    Before doing the same thing on ``"{{{val}}}".format(val)``

    Example:

        Let's say we're at ``images.my_image.persistence.image_name`` in the
        configuration.

        This means ``{_key_name_2}`` (which is from ``meta.key_names()``) is
        equal to ``my_image``.

        .. code-block:: python

            many_format(overridden("images.{_key_name_2}.image_name"), formatter=MergedOptionStringFormatter)

            # Is equivalent to

            formatted(overridden("{images.my_image.image_name}"), formatter=MergedOptionStringFormatter)

        This essentially means we can format a key in the options using other
        keys from the options!
    """
    def setup(self, spec, formatter, expected_type=NotSpecified):
        self.spec = spec
        self.formatter = formatter
        self.expected_type = expected_type

    def fake(self, meta, with_non_defaulted=False):
        return self.spec.fake_filled(meta, with_non_defaulted=with_non_defaulted)

    def normalise_either(self, meta, val):
        """Format the formatted spec"""
        val = self.spec.normalise(meta, val)
        done = []

        while True:
            fm = formatted(string_spec(), formatter=self.formatter, expected_type=str)
            normalised = fm.normalise(meta, val)
            if normalised == val:
                break

            if normalised in done:
                done.append(normalised)
                raise BadSpecValue("Recursive formatting", done=done, meta=meta)
            else:
                done.append(normalised)
                val = normalised

        return formatted(string_spec(), formatter=self.formatter, expected_type=self.expected_type).normalise(meta, "{{{0}}}".format(val))

@spec
class overridden(Spec):
    """
    Usage
        .. code-block:: python

            overridden(value).normalise(meta, val)

    This will return ``value`` regardless of what ``val`` is!
    """
    def setup(self, value):
        self.value = value

    def normalise(self, meta, val):
        return self.value

    def default(self, meta):
        return self.value

@spec
class any_spec(Spec):
    """
    Usage
        .. code-block:: python

            any_spec().normalise(meta, val)

    Will return ``val`` regardless of what ``val`` is.
    """
    def normalise(self, meta, val):
        return val

@spec
class container_spec(Spec):
    """
    Usage
        .. code-block:: python

            container_spec(kls, spec).normalise(meta, val)

    This will apply ``spec.normalise(meta, val)`` and call ``kls`` with the result
    of that as the one argument.

    .. note:: if the ``val`` is already ``isinstance(val, kls)`` then it will
      just return ``val``.
    """
    def setup(self, kls, spec):
        self.kls = kls
        self.spec = spec

    def fake(self, meta, with_non_defaulted=False):
        return self.kls(self.spec.fake_filled(meta, with_non_defaulted=with_non_defaulted))

    def normalise_either(self, meta, val):
        if isinstance(val, self.kls):
            return val
        return self.kls(self.spec.normalise(meta, val))

@spec
class delayed(Spec):
    """
    Usage
        .. code-block:: python

            delayed(spec).normalise(meta, val)

    This returns a function that when called will do ``spec.normalise(meta, val)``
    """
    def setup(self, spec):
        self.spec = spec

    def normalise_either(self, meta, val):
        return lambda: self.spec.normalise(meta, val)

    def fake(self, meta, with_non_defaulted=False):
        return lambda: self.spec.fake_filled(meta, with_non_defaulted=with_non_defaulted)

@spec
class typed(Spec):
    """
    Usage
        .. code-block:: python

            typed(kls).normalise(meta, val)

    This will return the value as is as long as it's isinstance of ``kls``

    Otherwise it complains that it's the wrong type
    """
    def setup(self, kls):
        self.kls = kls

    def normalise_filled(self, meta, val):
        if not isinstance(val, self.kls):
            raise BadSpecValue("Got the wrong type of value", expected=self.kls, got=type(val), meta=meta)
        return val

@spec
class has(Spec):
    """
    Usage
        .. code-block:: python

            has(prop1, prop2, ..., propn).normalise(meta, val)

    This will complain if the value does not have any of the specified
    properties (using hasattr)
    """

    def setup(self, *properties):
        self.properties = properties

    def normalise_filled(self, meta, val):
        missing = []
        for prop in self.properties:
            if not hasattr(val, prop):
                missing.append(prop)

        if missing:
            raise BadSpecValue("Value is missing required properties", required=self.properties, missing=missing, meta=meta)

        return val

@spec
class tuple_spec(Spec):
    """
    Usage
        .. code-block:: python

            tuple_spec(spec1, spec2, ..., specn).normalise(meta, val)

    Will complain if the value is not a tuple or doesn't have the same number
    of items as specified specs.

    Will complain if any of the specs fail for their respective part of val.

    Returns the result of running all the values through the specs as a tuple.
    """

    def setup(self, *specs):
        self.specs = specs

    def normalise_filled(self, meta, val):
        if type(val) is not tuple:
            raise BadSpecValue("Expected a tuple", got=type(val), meta=meta)

        if len(val) != len(self.specs):
            raise BadSpecValue("Expected tuple to be of a particular length", expected=len(self.specs), got=len(val), meta=meta)

        result = []
        errors = []
        for index, spec in enumerate(self.specs):
            try:
                result.append(spec.normalise(meta.indexed_at(index), val[index]))
            except BadSpecValue as error:
                errors.append(error)

        if errors:
            raise BadSpecValue("Value failed some specifications", _errors=errors, meta=meta)

        return tuple(result)

@spec
class none_spec(Spec):
    """
    Usage
        .. code-block:: python

            none_spec().normalise(meta, val)

    Will complain if the value is not None. Otherwise returns None.

    Defaults to None.
    """
    def normalise_empty(self, meta):
        return None

    def normalise_filled(self, meta, val):
        if val is None:
            return None
        else:
            raise BadSpecValue("Expected None", got=val, meta=meta)

@spec
class many_item_formatted_spec(Spec):
    """
    Usage
        .. code-block:: python

            class FinalKls(dictobj):
                fields = ["one", "two", ("three", None)]

            class my_special_spec(many_item_formatted_spec):
                specs = [integer_spec(), string_spec()]

                def create_result(self, one, two, three, meta, val, dividers):
                    if three is NotSpecified:
                        return FinalKls(one, two)
                    else:
                        return FinalKls(one, two, three)

                # The rest of the options are optional
                creates = FinalKls
                value_name = "special"
                seperators = "^"
                optional_specs = [boolean()]

            spec = my_special_spec()
            spec.normalise(meta, "1^tree") == FinalKls(1, "tree")
            spec.normalise(meta, [1, "tree"]) == FinalKls(1, "tree")
            spec.normalise(meta, [1, tree, False]) == FinalKls(1, "tree", False)

        We can also define modification hooks for each part of the spec:

        .. code-block:: python

            class my_special_spec(many_item_formatted_spec):
                specs = [integer_spec(), integer_spec(), integer_spec()]

                def spec_wrapper_2(self, spec, one, two, meta, val, dividers):
                    return defaulted(spec, one + two)

                def determine_2(self, meta, val):
                    return 42

                def alter_2(self, one, meta, original_two, val):
                    if one < 10:
                        return original_two
                    else:
                        return original_two * 10

                def alter_3(self, one, two, meta, original_three, val):
                    if two < 100:
                        return original_three
                    else:
                        return original_three * 100

                def create_result(self, one, two, three, meta, val, dividers):
                    return FinalKls(one, two, three)

    A spec for something that is many items
    Either a list or a string split by ":"

    If it's a string it will split by ':'
    Otherwise if it's a list, then it will use as is
    and will complain if it has two many values

    It will use determine_<num> on any value that is still NotSpecified after
    splitting the val.

    And will use alter_<num> on all values after they have been formatted.

    Where <num> is 1 indexed index of the value in the spec specifications.

    Finally, create_result is called at the end to create the final result from
    the determined/formatted/altered values.
    """
    specs = []
    creates = None
    value_name = None
    seperators = ":"
    optional_specs = []

    def setup(self, *args, **kwargs):
        """Setup our value_name if not already specified on the class"""
        if not self.value_name:
            self.value_name = self.__class__.__name__

    def create_result(*args):
        """Called by normalise with (*vals, meta, original_val, dividers)"""
        raise NotImplementedError()

    def normalise(self, meta, val):
        """Do the actual normalisation from a list to some result"""
        if self.creates is not None:
            if isinstance(val, self.creates):
                return val

        vals, dividers = self.split(meta, val)
        self.validate_split(vals, dividers, meta, val)

        for index, spec in enumerate(self.specs + self.optional_specs):
            expected_type = NotSpecified
            if isinstance(spec, (list, tuple)):
                spec, expected_type = spec

            args = [vals, dividers, expected_type, index+1, meta, val]

            self.determine_val(spec, *args)
            spec = self.determine_spec(spec, *args)
            self.alter(spec, *args)

        return self.create_result(*list(vals) + [meta, val, dividers])

    def determine_spec(self, spec, vals, dividers, expected_type, index, meta, original_val):
        return getattr(self, "spec_wrapper_{0}".format(index), lambda spec, *args: spec)(spec, *list(vals)[:index] + [meta, original_val, dividers])

    def determine_val(self, spec, vals, dividers, expected_type, index, meta, original_val):
        """
        Find a val and spec for this index in vals.

        Use self.determine_<index> to get a val

        Use self.spec_wrapper_<index> to get a spec

        Or just use the spec passed in and the value at the particular index in vals
        """
        val = NotSpecified
        if index <= len(vals):
            val = vals[index-1]
        if len(vals) < index:
            vals.append(val)

        val = getattr(self, "determine_{0}".format(index), lambda *args: val)(*list(vals)[:index] + [meta, original_val])
        vals[index-1] = val

    def alter(self, spec, vals, dividers, expected_type, index, meta, original_val):
        """
        Alter the val we found in self.determine_val

        If we have a formatter on the class, use that, otherwise just use the spec.

        After this, use self.alter_<index> if it exists
        """
        val = vals[index-1]
        specified = val is not NotSpecified
        not_optional = index - 1 < len(self.specs)
        no_expected_type = expected_type is NotSpecified
        not_expected_type = not isinstance(val, expected_type)

        if (not_optional or specified) and (no_expected_type or not_expected_type):
            val = self.normalise_val(spec, meta, val)

        altered = getattr(self, "alter_{0}".format(index), lambda *args: val)(*(vals[:index] + [val, meta, original_val]))
        vals[index-1] = altered

    def normalise_val(self, spec, meta, val):
        """
        Normalise with a spec

        If we have a formatter, use that as well
        """
        if getattr(self, "formatter", None):
            return formatted(spec, formatter=self.formatter).normalise(meta, val)
        else:
            return spec.normalise(meta, val)

    def validate_split(self, vals, dividers, meta, val):
        """Validate the vals against our list of specs"""
        if len(vals) < len(self.specs) or len(vals) > len(self.specs) + len(self.optional_specs):
            raise BadSpecValue("The value is a list with the wrong number of items"
                , got=val
                , meta=meta
                , got_length=len(vals)
                , min_length=len(self.specs)
                , max_length=len(self.specs) + len(self.optional_specs)
                , looking_at = self.value_name
                )

    def split(self, meta, val):
        """Split our original value based on our seperators"""
        if isinstance(val, (list, tuple)):
            vals = val
            dividers = [':'] * (len(val) - 1)

        elif isinstance(val, str):
            vals = []
            dividers = []
            if self.seperators:
                while val and any(seperator in val for seperator in self.seperators):
                    for seperator in self.seperators:
                        if seperator in val:
                            nxt, val = val.split(seperator, 1)
                            vals.append(nxt)
                            dividers.append(seperator)
                            break
                vals.append(val)

            if not vals:
                vals = [val]
                dividers=[None]

        elif isinstance(val, dict):
            if len(val) != 1:
                raise BadSpecValue("Value as a dict must only be one item", got=val, meta=meta)
            vals = list(val.items())[0]
            dividers = [':']

        else:
            vals = [val]
            dividers = []

        return vals, dividers
