"""
Validators are the same as any other subclass of
:class:`delfick_project.norms.sb.Spec` in that it has a ``normalise`` method
that takes in ``meta`` and ``val`` and returns a new ``val``.

It is convention that a validator subclasses :class:`delfick_project.norms.Validator`
and implements a ``validate`` method. This means ``sb.NotSpecified`` values are
ignored and any specified value goes through the ``validate`` method.

It is the job of the validator to raise a subclass of
:class:`delfick_project.norms.BadSpec` if something is wrong, otherwise just
return ``val``.
"""
from .errors import BadSpecValue, DeprecatedKey, BadSpecDefinition
from . import spec_base as sb

from itertools import chain
import re

default_validators = []

def register(func):
    """For the documentations!"""
    default_validators.append((func.__name__, func))
    return func

class Validator(sb.Spec):
    """
    A specification that either returns ``sb.NotSpecified`` if ``val`` is
    ``sb.NotSpecified`` or simply calls ``self.validate``.

    ``validate``
        A method to do validation on a value. if the value is invalid, it is best
        to raise an instance of ``delfick_project.norms.BadSpec``.
    """
    def validate(meta, val):
        raise NotImplementedError()

    def normalise_either(self, meta, val):
        if val is sb.NotSpecified:
            return val
        else:
            return self.validate(meta, val)

@register
class has_either(Validator):
    """
    Usage
        .. code-block:: python

            has_either([key1, ..., keyn]).normalise(meta, val)

    Will complain if the ``val.get(key, sb.NotSpecified)`` returns ``sb.NotSpecified``
    for all the choices.

    I.e. A valid dictionary has either one of the specified keys!
    """
    def setup(self, choices):
        self.choices = choices

    def validate(self, meta, val):
        """Complain if we have none of the choices"""
        if all(val.get(key, sb.NotSpecified) is sb.NotSpecified for key in self.choices):
            raise BadSpecValue("Need to specify atleast one of the required keys", choices=self.choices, meta=meta)
        return val

@register
class has_only_one_of(Validator):
    """
    Usage
        .. code-block:: python

            has_only_one_of([key1, ..., keyn]).normalise(meta, val)

    Will complain if the ``val.get(key, sb.NotSpecified)`` returns ``sb.NotSpecified``
    for all but one of the choices.

    I.e. A valid dictionary must have exactly one of the specified keys!
    """
    def setup(self, choices):
        if len(choices) < 1:
            raise BadSpecDefinition("Must specify atleast one choice", got=choices)
        self.choices = choices

    def validate(self, meta, val):
        """Complain if we don't have one of the choices"""
        if [val.get(key, sb.NotSpecified) is sb.NotSpecified for key in self.choices].count(True) != 1:
            raise BadSpecValue("Can only specify exactly one of the available choices", choices=self.choices, meta=meta)
        return val

@register
class either_keys(Validator):
    """
    Usage
        .. code-block:: python

            either_keys([k1, k2], [k3]).normalise(meta, val)

    Will complain if the value is not a dictionary

    Will complain if the keys from one group are mixed with keys from another group

    Will complain if keys from one group appear without the rest of the keys in that group

    Will not complain if unspecified keys are in the val
    """
    def setup(self, *choices):
        self.choices = choices
        found = set()
        duplicate = []
        for choice in choices:
            if type(choice) is not list:
                raise BadSpecDefinition("Each choice must be a list", got=choice)

            for key in choice:
                if key in found:
                    duplicate.append(key)
                else:
                    found.add(key)

        if duplicate:
            raise BadSpecDefinition("Found common keys in the choices", common=sorted(duplicate))

    def validate(self, meta, val):
        """Complain if we don't have a valid group"""
        if val is sb.NotSpecified:
            val = None

        val = sb.dictionary_spec().normalise(meta, val)
        associates = []
        perfect_association = []

        for index, group in enumerate(self.choices):
            other_choices = list(chain.from_iterable([self.choices[i] for i in range(len(self.choices)) if i != index]))

            found = []
            missing = []
            for key in group:
                if key not in val:
                    missing.append(key)
                else:
                    found.append(key)

            if found:
                associates.append(index)
                if not missing:
                    perfect_association.append(index)

        if len(perfect_association) == 0:
            if len(associates) == 0:
                raise BadSpecValue("Value associates with no groups", val=val, choices=self.choices, meta=meta)

            elif len(associates) == 1:
                group = self.choices[associates[0]]
                other_choices = list(chain.from_iterable([self.choices[i] for i in range(len(self.choices)) if i != associates[0]]))

                found = []
                invalid = []
                missing = []
                for key in group:
                    if key not in val:
                        missing.append(key)
                    else:
                        found.append(key)

                for key in other_choices:
                    if key in val:
                        invalid.append(key)

                raise BadSpecValue("Missing keys from this group", group=group, found=found, invalid=invalid, missing=missing, meta=meta)

            else:
                raise BadSpecValue("Value associates with multiple groups", associates=[self.choices[i] for i in associates], got=val, meta=meta)

        elif len(perfect_association) == 1:
            other_choices = list(chain.from_iterable([self.choices[i] for i in range(len(self.choices)) if i != perfect_association[0]]))
            invalid = []
            for key in other_choices:
                if key in val:
                    invalid.append(key)

            if invalid:
                raise BadSpecValue("Value associates with a group but has keys from other groups", associates_with=self.choices[perfect_association[0]], invalid=invalid, meta=meta)
            else:
                return val

        else:
            raise BadSpecValue("Value associates with multiple groups", associates=[self.choices[i] for i in perfect_association], got=val, meta=meta)

@register
class no_whitespace(Validator):
    """
    Usage
        .. code-block:: python

            no_whitespace().normalise(meta, val)

    Raises an error if we can find the regex ``\\s+`` in the ``val``.
    """
    def setup(self):
        self.regex = re.compile(r"\s+")

    def validate(self, meta, val):
        """Complain about whitespace"""
        if self.regex.search(val):
            raise BadSpecValue("Expected no whitespace", meta=meta, val=val)
        return val

@register
class no_dots(Validator):
    """
    Usage
        .. code-block:: python

            no_dots().normalise(meta, val)

            # or

            no_dots(reason="dots are evil!").normalise(meta, val)

    This will complain if ``val`` contains any dots

    It will use the ``reason`` to explain why it's an error if it's provided.
    """
    def setup(self, reason=None):
        self.reason = reason

    def validate(self, meta, val):
        """Complain about dots"""
        if '.' in val:
            reason = self.reason
            if not reason:
                reason = "Expected no dots"
            raise BadSpecValue(reason, meta=meta, val=val)
        return val

@register
class regexed(Validator):
    """
    Usage
        .. code-block:: python

            regexed(regex1, ..., regexn).normalise(meta, val)

    This will match the ``val`` against all the ``regex``s and will complain if
    any of them fail, otherwise the ``val`` is returned.
    """
    def setup(self, *regexes):
        self.regexes = [(regex, re.compile(regex)) for regex in regexes]

    def validate(self, meta, val):
        """Complain if the value doesn't match the regex"""
        for spec, regex in self.regexes:
            if not regex.match(val):
                raise BadSpecValue("Expected value to match regex, it didn't", spec=spec, meta=meta, val=val)
        return val

@register
class deprecated_key(Validator):
    """
    Usage
        .. code-block:: python

            deprecated_key(key, reason).normalise(meta, val)

    This will raise an error if ``val`` is nonempty and contains ``key``. The
    error will use ``reason`` in it's message.
    """
    def setup(self, key, reason):
        self.key = key
        self.reason = reason

    def validate(self, meta, val):
        """Complain if the key is in val"""
        if val and self.key in val:
            raise DeprecatedKey(key=self.key, reason=self.reason, meta=meta)

@register
class choice(Validator):
    """
    Usage
        .. code-block:: python

            choice(choice1, ..., choicen).normalise(meta, val)
    """
    def setup(self, *choices):
        self.choices = choices

    def validate(self, meta, val):
        """Complain if the key is not one of the correct choices"""
        if val not in self.choices:
            raise BadSpecValue("Expected the value to be one of the valid choices", got=val, choices=self.choices, meta=meta)
        return val
