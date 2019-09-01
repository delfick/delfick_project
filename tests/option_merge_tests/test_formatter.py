# coding: spec

from delfick_project.option_merge import MergedOptionStringFormatter, MergedOptions
from delfick_project.norms import sb

from unittest import mock
import pytest
import string


describe "MergedOptionStringFormatter":

    @pytest.fixture()
    def ms(self, autouse=True):
        class Mocks:
            all_options = mock.MagicMock(name="all_options")
            option_path = mock.Mock(name="option_path")
            chain = mock.Mock(name="chain")
            value = mock.Mock(name="value")

        return Mocks

    it "takes in all_options, option_path, chain and value", ms:
        formatter = MergedOptionStringFormatter(
            ms.all_options, ms.option_path, chain=ms.chain, value=ms.value
        )
        assert formatter.all_options is ms.all_options
        assert formatter.option_path is ms.option_path
        assert formatter.chain is ms.chain
        assert formatter.value is ms.value

    it "defaults chain to a list with option_path in it", ms:
        formatter = MergedOptionStringFormatter(ms.all_options, ms.option_path)
        assert formatter.chain == [ms.option_path]

    it "defaults value to sb.NotSpecified", ms:
        formatter = MergedOptionStringFormatter(ms.all_options, ms.option_path)
        assert formatter.value is sb.NotSpecified

    describe "format":
        it "returns the value if it's not a string", ms:
            value = mock.Mock(name="value")
            assert (
                MergedOptionStringFormatter(ms.all_options, ms.option_path, value=value).format()
            ) is value

        it "uses get_string if the value isn't specified", ms:
            ret = mock.Mock(name="ret")
            get_string = mock.Mock(name="get_string")
            get_string.return_value = ret

            formatter = MergedOptionStringFormatter(
                ms.all_options, ms.option_path, value=sb.NotSpecified
            )
            with mock.patch.object(formatter, "get_string", get_string):
                assert formatter.format() is ret

            get_string.assert_called_once_with(ms.option_path)

        it "calls format on super if the value is a string", ms:
            result = mock.Mock(name="result")
            format_func = mock.Mock(name="format", return_value=result)

            with mock.patch.object(string.Formatter, "format", format_func):
                assert (
                    MergedOptionStringFormatter(
                        ms.all_options, ms.option_path, value="asdf"
                    ).format()
                ) is result

            format_func.assert_called_once_with("asdf")

    describe "with_option_path":
        it "appends value to the chain, sets option_path to the value and sets value to sb.NotSpecified", ms:
            one = MergedOptionStringFormatter(ms.all_options, ms.option_path, chain=[1], value=2)
            two = one.with_option_path(3)
            assert two.all_options is ms.all_options
            assert two.option_path is 3
            assert two.chain == [1, 3]
            assert two.value is sb.NotSpecified

    describe "get_string":
        it "gets the key from all_options", ms:
            meh = mock.Mock(name="meh")
            blah = mock.Mock(name="blah")
            all_options = {meh: blah}

            assert (
                MergedOptionStringFormatter(all_options, ms.option_path).get_string(meh)
            ) is blah

    describe "get_field":
        it "returns special if special_get_field returns something", ms:
            ret = mock.Mock(name="ret")
            special_get_field = mock.Mock(name="special_get_field")
            special_get_field.return_value = ret

            args = mock.Mock(name="args")
            value = mock.Mock(name="value")
            kwargs = mock.Mock(name="kwargs")
            format_spec = mock.Mock(name="format_spec")

            formatter = MergedOptionStringFormatter(ms.all_options, ms.option_path)
            with mock.patch.object(formatter, "special_get_field", special_get_field):
                assert formatter.get_field(value, args, kwargs, format_spec=format_spec) is ret

            special_get_field.assert_called_once_with(value, args, kwargs, format_spec)

        it "Clones the formatter with value as the option_path and formats it", ms:
            ret = mock.Mock(name="ret")
            cloned = mock.Mock(name="cloned")
            cloned.format.return_value = ret

            with_option_path = mock.Mock(name="with_option_path")
            with_option_path.return_value = cloned

            special_get_field = mock.Mock(name="special_get_field", return_value=None)

            args = mock.Mock(name="args")
            value = mock.Mock(name="value")
            kwargs = mock.Mock(name="kwargs")
            format_spec = mock.Mock(name="format_spec")

            formatter = MergedOptionStringFormatter(ms.all_options, ms.option_path)
            with mock.patch.multiple(
                formatter, special_get_field=special_get_field, with_option_path=with_option_path
            ):
                assert formatter.get_field(value, args, kwargs, format_spec=format_spec) == (
                    ret,
                    (),
                )

            special_get_field.assert_called_once_with(value, args, kwargs, format_spec)
            with_option_path.assert_called_once_with(value)

    describe "format_field":
        it "returns special_format_field if it returns a value", ms:
            ret = mock.Mock(name="ret")
            special_format_field = mock.Mock(name="special_format_field")
            special_format_field.return_value = ret

            obj = mock.Mock(name="obj")
            format_spec = mock.Mock(name="format_spec")

            formatter = MergedOptionStringFormatter(ms.all_options, ms.option_path)
            with mock.patch.object(formatter, "special_format_field", special_format_field):
                assert formatter.format_field(obj, format_spec) is ret

            special_format_field.assert_called_once_with(obj, format_spec)

        it "returns the obj if it's a dictionary", ms:

            class blah(dict):
                pass

            obj = blah()

            format_spec = mock.Mock(name="format_spec")
            special_format_field = mock.Mock(name="special_format_field", return_value=None)

            formatter = MergedOptionStringFormatter(ms.all_options, ms.option_path)
            with mock.patch.object(formatter, "special_format_field", special_format_field):
                assert formatter.format_field(obj, format_spec) is obj

            special_format_field.assert_called_once_with(obj, format_spec)

        it "returns the object if asks for it", ms:

            class Obj(object):
                _merged_options_formattable = True

            obj = Obj()

            format_spec = mock.Mock(name="format_spec")
            special_format_field = mock.Mock(name="special_format_field", return_value=None)

            formatter = MergedOptionStringFormatter(ms.all_options, ms.option_path)
            with mock.patch.object(formatter, "special_format_field", special_format_field):
                assert formatter.format_field(obj, format_spec) is obj

            special_format_field.assert_called_once_with(obj, format_spec)

        it "returns the object if it's a mock", ms:
            obj = mock.Mock(name="obj")

            format_spec = mock.Mock(name="format_spec")
            special_format_field = mock.Mock(name="special_format_field", return_value=None)

            formatter = MergedOptionStringFormatter(ms.all_options, ms.option_path)
            with mock.patch.object(formatter, "special_format_field", special_format_field):
                assert formatter.format_field(obj, format_spec) is obj

            special_format_field.assert_called_once_with(obj, format_spec)

        it "returns the obj if it's a lambda or function or method", ms:

            class blah(dict):
                def method(s):
                    pass

            def func(s):
                pass

            lamb = lambda: 1
            obj = blah()

            format_spec = mock.Mock(name="format_spec")
            special_format_field = mock.Mock(name="special_format_field", return_value=None)

            for callable_obj in (obj.method, func, lamb, sum):
                formatter = MergedOptionStringFormatter(ms.all_options, ms.option_path)
                with mock.patch.object(formatter, "special_format_field", special_format_field):
                    assert formatter.format_field(callable_obj, format_spec) is callable_obj

        it "does an actual format_field if no special and obj is not a dict", ms:
            obj = "shizzle"

            format_spec = mock.Mock(name="format_spec")
            special_format_field = mock.Mock(name="special_format_field", return_value=None)

            ret = mock.Mock(name="ret")
            super_format_field = mock.Mock(name="super_format_field", return_value=ret)

            formatter = MergedOptionStringFormatter(ms.all_options, ms.option_path)
            with mock.patch.object(string.Formatter, "format_field", super_format_field):
                with mock.patch.object(formatter, "special_format_field", special_format_field):
                    assert formatter.format_field(obj, format_spec) is ret

            special_format_field.assert_called_once_with(obj, format_spec)

    describe "_vformat":
        it "returns the object if only formatting one item":
            blah = type("blah", (dict,), {})()
            all_options = {"meh": blah}

            args = mock.Mock(name="args")
            kwargs = mock.Mock(name="kwargs")
            used_args = set([mock.Mock(name="used_args")])

            formatter = MergedOptionStringFormatter(all_options, "meh")
            special_get_field = mock.Mock(name="special_get_field", return_value=None)
            special_format_field = mock.Mock(name="special_format_field", return_value=None)

            with mock.patch.multiple(
                formatter,
                special_get_field=special_get_field,
                special_format_field=special_format_field,
            ):
                assert formatter._vformat("{meh}", args, kwargs, used_args, 2) is blah

        it "concatenates the strings together if this is multiple things to be formatted":
            blah = type("blah", (dict,), {})({"1": "2"})
            all_options = {"meh": blah, "wat": "ever"}

            args = mock.Mock(name="args")
            kwargs = mock.Mock(name="kwargs")
            used_args = set([mock.Mock(name="used_args")])

            formatter = MergedOptionStringFormatter(all_options, "meh")
            special_get_field = mock.Mock(name="special_get_field", return_value=None)
            special_format_field = mock.Mock(name="special_format_field", return_value=None)

            with mock.patch.multiple(
                formatter,
                special_get_field=special_get_field,
                special_format_field=special_format_field,
            ):
                assert (
                    formatter._vformat("{meh}and{wat}", args, kwargs, used_args, 2)
                    == "{'1': '2'}andever"
                )

describe "Custom MergedOptionStringFormatter":
    it "works":

        class MyStringFormatter(MergedOptionStringFormatter):
            def special_format_field(s, obj, format_spec):
                if format_spec == "upper":
                    return obj.upper()

                if format_spec == "no_interpret":
                    return obj

            def special_get_field(s, value, args, kwargs, format_spec=None):
                if format_spec == "no_interpret":
                    return value, ()

        all_options = MergedOptions.using(
            {"yeap": "yessir", "blah": "notused"}, {"blah": {"things": "stuff", "la": "delala"}}
        )
        formatter = MyStringFormatter(
            all_options, "whatever", value="{yeap} and {blah.things:upper} {blah.la:no_interpret}"
        )
        assert formatter.format() == "yessir and STUFF blah.la"

    it "formats what it finds":

        class MyStringFormatter(MergedOptionStringFormatter):
            def special_format_field(s, obj, format_spec):
                pass

            def special_get_field(s, value, args, kwargs, format_spec=None):
                pass

        all_options = MergedOptions.using({"one": "{two}", "two": "three"})
        formatter = MyStringFormatter(all_options, "one", value="{one}")
        assert formatter.format() == "three"
