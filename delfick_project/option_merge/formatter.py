"""
MergedOptionStringFormatter is provided as a base class for creating a special
formatter that can format strings using a MergedOptions object.

.. code-block:: python

    from delfick_project.option_merge import MergedOptionStringFormatter, MergedOptions

    class Formatter(MergedOptionStringFormatter):
        custom_format_specs = ["env"]

        def special_format_field(self, obj, format_spec):
            if format_spec == "env":
                return "${{{0}}}".format(obj)

    m = MergedOptions.using({"a": {"b": 3}, "c": 5, "d": "{c}"})
    formatted = Formatter(m, "a.b: {a.b}, d: {d} and c={c} and d={BLAH:env}").format()
    assert formatted == "a.b: 3, d: 5 and c=5 and d=${BLAH}"
"""

from .merge import MergedOptions

from delfick_project.errors import DelfickError
from delfick_project.norms import Meta

import string
import types


class BadOptionFormat(DelfickError):
    pass


class NoFormat(object):
    """Used to tell when to stop formatting a string"""

    def __init__(self, val):
        self.val = val


class MergedOptionStringFormatter(string.Formatter):
    """
    Resolve format options into a MergedOptions dictionary
    """

    custom_format_specs = []

    def __init__(self, all_options, value, chain=None):
        if chain is None:
            chain = []
        self.chain = chain
        self.value = value
        self.all_options = all_options
        super(MergedOptionStringFormatter, self).__init__()

    def format(self):
        """Format our value into all_options"""
        val = self.value

        if isinstance(val, NoFormat):
            return val.val
        if not isinstance(val, str):
            return val
        return super().format(val)

    def special_get_field(self, value, args, kwargs, format_spec=None):
        """
        Complain about recursive options and return value as is for custom_format_specs
        """
        if value in self.chain:
            raise BadOptionFormat("Recursive option", chain=self.chain + [value])

        if format_spec in self.custom_format_specs:
            return value, ()

    def special_format_field(self, obj, format_spec):
        """
        In this function you match against ``format_spec`` and return either a
        formatted version of ``obj`` or None.

        .. code-block:: python

            class MyFormatter(MergedOptionStringFormatter):
                custom_format_specs = ["plus_one"]

                def special_format_field(obj, format_spec):
                    if format_spec == "plus_one":
                        return int(obj) + 1

            formatted = MyFormatter({}, "", value="{3:plus_one}").format()
            assert formatted == 4
        """

    def get_string(self, key):
        """
        Get a string from all_options

        it is recommended you override this method and raise an error if the key
        does not exist in self.all_options..
        """
        if key not in self.all_options:
            kwargs = {}
            if len(self.chain) > 1:
                kwargs["source"] = Meta(self.all_options, self.chain[-2]).source
            raise BadOptionFormat("Can't find key in options", key=key, chain=self.chain, **kwargs)
        return self.all_options[key]

    def get_field(self, value, args, kwargs, format_spec=None):
        """Also take the spec into account"""
        special = self.special_get_field(value, args, kwargs, format_spec)
        if special is not None:
            return special
        else:
            val = self.get_string(value)
            f = self.__class__(self.all_options, val, chain=self.chain + [value])
            return f.format(), ()

    def format_field(self, obj, format_spec):
        """Know about any special formats"""
        special = self.special_format_field(obj, format_spec)
        if special:
            return special
        else:
            is_dict = type(obj) is MergedOptions or isinstance(obj, dict)
            is_a_mock = hasattr(obj, "mock_calls")
            is_special_type = any(
                isinstance(obj, typ)
                for typ in (
                    types.LambdaType,
                    types.FunctionType,
                    types.MethodType,
                    types.BuiltinFunctionType,
                    types.BuiltinMethodType,
                )
            )
            is_formattable = getattr(obj, "_merged_options_formattable", False)

            if is_dict or is_special_type or is_a_mock or is_formattable:
                return obj
            else:
                return super(MergedOptionStringFormatter, self).format_field(obj, format_spec)

    def vformat(self, format_string, args, kwargs):
        """This changes in 3.5.1 and I want it to not have changed"""
        used_args = set()
        result = self._vformat(format_string, args, kwargs, used_args, 2)
        self.check_unused_args(used_args, args, kwargs)
        return result

    def _vformat(self, format_string, args, kwargs, used_args, recursion_depth):
        """I really want to know what the format_string is so I'm taking from standard library string and modifying slightly"""
        if recursion_depth < 0:
            raise ValueError("Max string recursion exceeded")

        result = []

        for literal_text, field_name, format_spec, conversion in self.parse(format_string):

            # output the literal text
            if literal_text:
                result.append(literal_text)

            # if there's a field, output it
            if field_name is not None:
                # this is some markup, find the object and do
                #  the formatting

                # given the field_name, find the object it references
                #  and the argument it came from
                # Slight modification here to pass in the format_spec
                obj, arg_used = self.get_field(field_name, args, kwargs, format_spec)
                used_args.add(arg_used)

                # do any conversion on the resulting object
                obj = self.convert_field(obj, conversion)

                # expand the format spec, if needed
                format_spec = self._vformat(
                    format_spec, args, kwargs, used_args, recursion_depth - 1
                )

                # format the object and append to the result
                result.append(self.format_field(obj, format_spec))

        if len(result) == 1:
            return result[0]
        return "".join(str(obj) for obj in result)

    def no_format(self, val):
        """Return an instance that is recognised by the formatter as no more formatting required"""
        return NoFormat(val)


__all__ = ["NoFormat", "MergedOptionStringFormatter"]
