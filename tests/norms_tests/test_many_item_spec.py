# coding: spec

from input_algorithms.many_item_spec import many_item_formatted_spec
from input_algorithms.spec_base import NotSpecified
from input_algorithms.errors import BadSpecValue
from input_algorithms.meta import Meta

from tests.helpers import TestCase

from noseOfYeti.tokeniser.support import noy_sup_setUp
import mock
import six

describe TestCase, "many_item_formatted_spec":
    before_each:
        self.val = mock.Mock(name="val")
        self.dividers = mock.Mock(name="dividers")
        self.spec = mock.Mock(name="spec", spec_set=["normalise", "spec"])
        self.meta = mock.Mock(name="meta", spec=Meta)
        self.original_val = mock.Mock(name="original_val", spec_set=[])
        self.expected_type = type("expected_type", (object,), {})
        self.many_item_spec = many_item_formatted_spec()
        self.formatter = mock.MagicMock(name="formatter", spec_set=["normalise", "__call__"])

    it "it sets value_name to the class name if not set":

        class Blah(many_item_formatted_spec):
            value_name = "stuff"

        class Meh(many_item_formatted_spec):
            pass

        assert Blah().value_name == "stuff"
        assert Meh().value_name == "Meh"

    describe "normalise":
        it "does nothing if the value is already self.creates type":
            val = self.expected_type()

            class Yeap(many_item_formatted_spec):
                creates = self.expected_type

            assert Yeap().normalise(self.meta, val) is val

        it "matches up the vals to the specs and passes through create_spec":
            spec1 = mock.Mock(name="spec1")
            spec1.normalise.return_value = "spec1_normalised"

            spec2 = mock.Mock(name="spec2")
            spec2.normalise.return_value = "spec2_normalised"

            spec3 = mock.Mock(name="spec3")
            spec3.normalise.return_value = "spec3_normalised"

            val1 = mock.Mock(name="val1")
            val2 = mock.Mock(name="val2")
            val3 = mock.Mock(name="val3")
            result = mock.Mock(name="result")

            vals = [val1, val2, val3]
            dividers = [":", ":"]
            split = mock.Mock(name="split")
            split.return_value = (vals, dividers)

            class Yeap(many_item_formatted_spec):
                specs = [spec1, spec2]
                optional_specs = [spec3]

                def determine_2(slf, pval1, pval2, meta, original_value):
                    assert pval1 is "spec1_normalised"
                    assert pval2 is val2
                    return "spec2_determined"

                def alter_3(slf, pval1, pval2, pval3, pval3_normalised, meta, original_value):
                    assert pval1 is "spec1_normalised"
                    assert pval2 is "spec2_normalised"
                    assert pval3 is val3
                    assert pval3_normalised is "spec3_normalised"
                    assert meta is self.meta
                    assert original_value is self.val
                    assert dividers == [":", ":"]
                    return "spec3_altered"

                def create_result(slf, pval1, pval2, pval3, meta, original_val, dividers):
                    assert pval1 is "spec1_normalised"
                    assert pval2 is "spec2_normalised"
                    assert pval3 is "spec3_altered"
                    assert meta is self.meta
                    assert original_val is self.val
                    assert dividers == [":", ":"]
                    return result

            yeap = Yeap()
            with mock.patch.object(yeap, "split", split):
                assert yeap.normalise(self.meta, self.val) is result

            spec1.normalise.assert_called_once_with(self.meta, val1)
            spec2.normalise.assert_called_once_with(self.meta, "spec2_determined")
            spec3.normalise.assert_called_once_with(self.meta, val3)

    describe "determine_val":
        it "Uses NotSpecified if vals is smaller than the index":
            vals = []
            dividers = []
            self.many_item_spec.determine_val(
                self.spec, vals, dividers, self.expected_type, 1, self.meta, self.original_val
            )
            assert vals == [NotSpecified]

        it "appends the val to vals and dividers if vals is not big enough":
            vals = [1]
            dividers = [":"]
            self.many_item_spec.determine_val(
                self.spec, vals, dividers, self.expected_type, 2, self.meta, self.original_val
            )
            assert vals[1] == NotSpecified
            assert vals == [1, NotSpecified]

        it "uses determine_<index> on the value":

            class Yeap(many_item_formatted_spec):
                def determine_2(slf, val1, val2, meta, original_val):
                    assert meta is self.meta
                    assert original_val is self.original_val
                    return (val1, 2)

            vals = [1]
            dividers = [":"]
            Yeap().determine_val(
                self.spec, vals, dividers, self.expected_type, 2, self.meta, self.original_val
            )
            assert vals[1] == (1, 2)
            assert vals == [1, (1, 2)]

    describe "determine_spec":
        it "uses spec_wrapper_<index> on the spec":
            vals = [1, 2]
            dividers = [":"]
            altered_spec = mock.Mock(name="altered_spec")

            class Yeap(many_item_formatted_spec):
                def spec_wrapper_2(slf, spec, val1, val2, meta, original_val, dividers):
                    assert spec is self.spec
                    assert meta is self.meta
                    assert original_val is self.original_val
                    return altered_spec

            new_spec = Yeap().determine_spec(
                self.spec, vals, dividers, self.expected_type, 2, self.meta, self.original_val
            )
            assert new_spec == altered_spec

    describe "alter":
        before_each:
            self.normalise_val = mock.Mock(name="normalise_val")

        it "does nothing if it's optional and not specified":
            val = NotSpecified
            vals = [val]

            self.normalise_val.return_value = mock.Mock(name="normalise_val")
            with mock.patch.object(self.many_item_spec, "normalise_val", self.normalise_val):
                self.many_item_spec.alter(
                    self.spec, vals, [], self.expected_type, 1, self.meta, self.original_val
                )

            assert vals == [val]
            assert len(self.normalise_val.mock_calls) == 0

        it "normalises the value if optional, but has a value":
            val = mock.Mock(name="value")
            normalised = mock.Mock(name="normalised")
            vals = [val]

            self.normalise_val.return_value = normalised
            with mock.patch.object(self.many_item_spec, "normalise_val", self.normalise_val):
                self.many_item_spec.alter(
                    self.spec, vals, [], self.expected_type, 1, self.meta, self.original_val
                )

            assert vals == [normalised]
            self.normalise_val.assert_called_once_with(self.spec, self.meta, val)

        it "does nothing if already the expected type":
            val = "yeap"
            vals = [val]

            self.normalise_val.return_value = mock.Mock(name="normalise_val")
            with mock.patch.object(self.many_item_spec, "normalise_val", self.normalise_val):
                self.many_item_spec.alter(self.spec, vals, [], str, 1, self.meta, self.original_val)

            assert vals == [val]
            assert len(self.normalise_val.mock_calls) == 0

        it "normalises the value if not the expected type":
            val = "value"
            normalised = mock.Mock(name="normalised")
            vals = [val]

            self.normalise_val.return_value = normalised
            with mock.patch.object(self.many_item_spec, "normalise_val", self.normalise_val):
                self.many_item_spec.alter(
                    self.spec, vals, [], bool, 1, self.meta, self.original_val
                )

            assert vals == [normalised]
            self.normalise_val.assert_called_once_with(self.spec, self.meta, val)

        it "alters the value after normalising it":
            val = "value"
            altered = mock.Mock(name="altered")
            normalised = mock.Mock(name="normalised")
            vals = [val]

            class Yeap(many_item_formatted_spec):
                def alter_1(slf, val1, normalised_val, meta, original_val):
                    assert val1 is val
                    assert normalised_val is normalised
                    assert meta is self.meta
                    assert original_val is self.original_val
                    return altered

            yeap = Yeap()
            self.normalise_val.return_value = normalised
            with mock.patch.object(yeap, "normalise_val", self.normalise_val):
                yeap.alter(self.spec, vals, [NotSpecified], bool, 1, self.meta, self.original_val)

            assert vals == [altered]
            self.normalise_val.assert_called_once_with(self.spec, self.meta, val)

    describe "normalise_val":
        it "uses formatted if a formatter has been specified":
            val = mock.Mock(name="value")
            formatted_instance = mock.Mock(name="formatted_instance")
            formatted = mock.Mock(name="formatted", return_value=formatted_instance)
            the_formatter = mock.Mock(name="formatter")
            normalised = mock.Mock(name="normalised")
            formatted_instance.normalise.return_value = normalised

            class Yeap(many_item_formatted_spec):
                formatter = the_formatter

            with mock.patch("input_algorithms.many_item_spec.formatted", formatted):
                assert Yeap().normalise_val(self.spec, self.meta, val) is normalised

            formatted.assert_called_with(self.spec, formatter=the_formatter)
            formatted_instance.normalise.assert_called_once_with(self.meta, val)

        it "just uses the spec if no formatter":
            val = mock.Mock(name="value")
            formatted = mock.Mock(name="formatted")
            the_formatter = mock.Mock(name="formatter")
            normalised = mock.Mock(name="normalised")
            self.spec.normalise.return_value = normalised

            class Yeap(many_item_formatted_spec):
                pass

            with mock.patch("input_algorithms.many_item_spec.formatted", formatted):
                assert Yeap().normalise_val(self.spec, self.meta, val) is normalised

            assert len(formatted.mock_calls) == 0
            self.spec.normalise.assert_called_once_with(self.meta, val)

    describe "validate_split":
        it "complains if number of vals is smaller than mandatory specs":
            vals = [1]

            class Yeap(many_item_formatted_spec):
                specs = [1, 2]

            with self.fuzzyAssertRaisesError(
                BadSpecValue, "The value is a list with the wrong number of items"
            ):
                Yeap().validate_split(vals, self.dividers, self.meta, self.val)

        it "complains if number of vals is greater than sum of mandatory and optional specs":
            vals = [1, 2, 3, 4, 5, 6, 7, 8]

            class Yeap(many_item_formatted_spec):
                specs = [1, 2]
                optional_specs = [3, 4]

            with self.fuzzyAssertRaisesError(
                BadSpecValue, "The value is a list with the wrong number of items"
            ):
                Yeap().validate_split(vals, self.dividers, self.meta, self.val)

    describe "split":
        it "sets default dividers to colon and vals to the val if already a list":
            vals = [1, 2, 3, 4]
            result = self.many_item_spec.split(self.meta, vals)
            assert result == (vals, [":", ":", ":"])

        it "complains if val is a dict without only one item":
            with self.fuzzyAssertRaisesError(BadSpecValue, "Value as a dict must only be one item"):
                self.many_item_spec.split(self.meta, {})

            with self.fuzzyAssertRaisesError(BadSpecValue, "Value as a dict must only be one item"):
                self.many_item_spec.split(self.meta, {1: 2, 3: 4})

        it "sets vals to the first key and val and dividers to a colon if val is a one item dict":
            result = self.many_item_spec.split(self.meta, {1: 2})
            assert result == ((1, 2), [":"])

        it "sets vals to a list with the val and dividers to nothing if not a list, string or dict":
            val = mock.Mock(name="value")
            result = self.many_item_spec.split(self.meta, val)
            assert result == ([val], [])

        describe "if val is a string":
            it "sets vals to the one val if no seperators specified":

                class Yeap(many_item_formatted_spec):
                    seperators = None

                assert Yeap().split(self.meta, "hello") == (["hello"], [None])

            it "splits by the available seperators and accumulates both":

                class Yeap(many_item_formatted_spec):
                    seperators = ":/="

                val = "hello:there/what_ya:doing=huh?"
                expected_val = ["hello", "there/what_ya", "doing", "huh?"]
                expected_dividers = [":", ":", "="]
                assert Yeap().split(self.meta, val) == (expected_val, expected_dividers)
