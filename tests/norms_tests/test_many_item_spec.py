# coding: spec

from delfick_project.norms import sb, BadSpecValue, Meta

from delfick_project.errors_pytest import assertRaises

from unittest import mock
import pytest


@pytest.fixture()
def meta():
    return Meta.empty()


@pytest.fixture()
def spec():
    return sb.many_item_formatted_spec()


describe "many_item_formatted_spec":

    @pytest.fixture()
    def ms(self):
        class Mocks:
            val = mock.Mock(name="val")
            dividers = mock.Mock(name="dividers")
            spec = mock.Mock(name="spec", spec_set=["normalise", "spec"])
            original_val = mock.Mock(name="original_val", spec_set=[])
            expected_type = type("expected_type", (object,), {})
            formatter = mock.MagicMock(name="formatter", spec_set=["normalise", "__call__"])
            normalise_val = mock.Mock(name="normalise_val")

        return Mocks

    it "it sets value_name to the class name if not set":

        class Blah(sb.many_item_formatted_spec):
            value_name = "stuff"

        class Meh(sb.many_item_formatted_spec):
            pass

        assert Blah().value_name == "stuff"
        assert Meh().value_name == "Meh"

    describe "normalise":
        it "does nothing if the value is already self.creates type", meta, ms:
            val = ms.expected_type()

            class Yeap(sb.many_item_formatted_spec):
                creates = ms.expected_type

            assert Yeap().normalise(meta, val) is val

        it "matches up the vals to the specs and passes through create_spec", meta, ms:
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

            class Yeap(sb.many_item_formatted_spec):
                specs = [spec1, spec2]
                optional_specs = [spec3]

                def determine_2(slf, pval1, pval2, meta, original_value):
                    assert pval1 == "spec1_normalised"
                    assert pval2 == val2
                    return "spec2_determined"

                def alter_3(slf, pval1, pval2, pval3, pval3_normalised, m, original_value):
                    assert pval1 == "spec1_normalised"
                    assert pval2 == "spec2_normalised"
                    assert pval3 is val3
                    assert pval3_normalised == "spec3_normalised"
                    assert m is meta
                    assert original_value is ms.val
                    assert dividers == [":", ":"]
                    return "spec3_altered"

                def create_result(slf, pval1, pval2, pval3, m, original_val, dividers):
                    assert pval1 == "spec1_normalised"
                    assert pval2 == "spec2_normalised"
                    assert pval3 == "spec3_altered"
                    assert m is meta
                    assert original_val is ms.val
                    assert dividers == [":", ":"]
                    return result

            yeap = Yeap()
            with mock.patch.object(yeap, "split", split):
                assert yeap.normalise(meta, ms.val) is result

            spec1.normalise.assert_called_once_with(meta, val1)
            spec2.normalise.assert_called_once_with(meta, "spec2_determined")
            spec3.normalise.assert_called_once_with(meta, val3)

    describe "determine_val":
        it "Uses sb.NotSpecified if vals is smaller than the index", spec, meta, ms:
            vals = []
            dividers = []
            spec.determine_val(ms.spec, vals, dividers, ms.expected_type, 1, meta, ms.original_val)
            assert vals == [sb.NotSpecified]

        it "appends the val to vals and dividers if vals is not big enough", spec, meta, ms:
            vals = [1]
            dividers = [":"]
            spec.determine_val(ms.spec, vals, dividers, ms.expected_type, 2, meta, ms.original_val)
            assert vals[1] == sb.NotSpecified
            assert vals == [1, sb.NotSpecified]

        it "uses determine_<index> on the value", meta, ms:

            class Yeap(sb.many_item_formatted_spec):
                def determine_2(slf, val1, val2, m, original_val):
                    assert m is meta
                    assert original_val is ms.original_val
                    return (val1, 2)

            vals = [1]
            dividers = [":"]
            Yeap().determine_val(
                ms.spec, vals, dividers, ms.expected_type, 2, meta, ms.original_val
            )
            assert vals[1] == (1, 2)
            assert vals == [1, (1, 2)]

    describe "determine_spec":
        it "uses spec_wrapper_<index> on the spec", meta, ms:
            vals = [1, 2]
            dividers = [":"]
            altered_spec = mock.Mock(name="altered_spec")

            class Yeap(sb.many_item_formatted_spec):
                def spec_wrapper_2(slf, spec, val1, val2, m, original_val, dividers):
                    assert spec is ms.spec
                    assert m is meta
                    assert original_val is ms.original_val
                    return altered_spec

            new_spec = Yeap().determine_spec(
                ms.spec, vals, dividers, ms.expected_type, 2, meta, ms.original_val
            )
            assert new_spec == altered_spec

    describe "alter":
        it "does nothing if it's optional and not specified", spec, meta, ms:
            val = sb.NotSpecified
            vals = [val]

            ms.normalise_val.return_value = mock.Mock(name="normalise_val")
            with mock.patch.object(spec, "normalise_val", ms.normalise_val):
                spec.alter(ms.spec, vals, [], ms.expected_type, 1, meta, ms.original_val)

            assert vals == [val]
            assert len(ms.normalise_val.mock_calls) == 0

        it "normalises the value if optional, but has a value", spec, meta, ms:
            val = mock.Mock(name="value")
            normalised = mock.Mock(name="normalised")
            vals = [val]

            ms.normalise_val.return_value = normalised
            with mock.patch.object(spec, "normalise_val", ms.normalise_val):
                spec.alter(ms.spec, vals, [], ms.expected_type, 1, meta, ms.original_val)

            assert vals == [normalised]
            ms.normalise_val.assert_called_once_with(ms.spec, meta, val)

        it "does nothing if already the expected type", spec, meta, ms:
            val = "yeap"
            vals = [val]

            ms.normalise_val.return_value = mock.Mock(name="normalise_val")
            with mock.patch.object(spec, "normalise_val", ms.normalise_val):
                spec.alter(ms.spec, vals, [], str, 1, meta, ms.original_val)

            assert vals == [val]
            assert len(ms.normalise_val.mock_calls) == 0

        it "normalises the value if not the expected type", spec, meta, ms:
            val = "value"
            normalised = mock.Mock(name="normalised")
            vals = [val]

            ms.normalise_val.return_value = normalised
            with mock.patch.object(spec, "normalise_val", ms.normalise_val):
                spec.alter(ms.spec, vals, [], bool, 1, meta, ms.original_val)

            assert vals == [normalised]
            ms.normalise_val.assert_called_once_with(ms.spec, meta, val)

        it "alters the value after normalising it", meta, ms:
            val = "value"
            altered = mock.Mock(name="altered")
            normalised = mock.Mock(name="normalised")
            vals = [val]

            class Yeap(sb.many_item_formatted_spec):
                def alter_1(slf, val1, normalised_val, m, original_val):
                    assert val1 is val
                    assert normalised_val is normalised
                    assert m is meta
                    assert original_val is ms.original_val
                    return altered

            yeap = Yeap()
            ms.normalise_val.return_value = normalised
            with mock.patch.object(yeap, "normalise_val", ms.normalise_val):
                yeap.alter(ms.spec, vals, [sb.NotSpecified], bool, 1, meta, ms.original_val)

            assert vals == [altered]
            ms.normalise_val.assert_called_once_with(ms.spec, meta, val)

    describe "normalise_val":
        it "uses formatted if a formatter has been specified", meta, ms:
            val = mock.Mock(name="value")
            formatted_instance = mock.Mock(name="formatted_instance")
            formatted = mock.Mock(name="formatted", return_value=formatted_instance)
            the_formatter = mock.Mock(name="formatter")
            normalised = mock.Mock(name="normalised")
            formatted_instance.normalise.return_value = normalised

            class Yeap(sb.many_item_formatted_spec):
                formatter = the_formatter

            with mock.patch("delfick_project.norms.spec_base.formatted", formatted):
                assert Yeap().normalise_val(ms.spec, meta, val) is normalised

            formatted.assert_called_with(ms.spec, formatter=the_formatter)
            formatted_instance.normalise.assert_called_once_with(meta, val)

        it "just uses the spec if no formatter", meta, ms:
            val = mock.Mock(name="value")
            formatted = mock.Mock(name="formatted")
            normalised = mock.Mock(name="normalised")
            ms.spec.normalise.return_value = normalised

            class Yeap(sb.many_item_formatted_spec):
                pass

            with mock.patch("delfick_project.norms.spec_base.formatted", formatted):
                assert Yeap().normalise_val(ms.spec, meta, val) is normalised

            assert len(formatted.mock_calls) == 0
            ms.spec.normalise.assert_called_once_with(meta, val)

    describe "validate_split":
        it "complains if number of vals is smaller than mandatory specs", meta, ms:
            vals = [1]

            class Yeap(sb.many_item_formatted_spec):
                specs = [1, 2]

            with assertRaises(BadSpecValue, "The value is a list with the wrong number of items"):
                Yeap().validate_split(vals, ms.dividers, meta, ms.val)

        it "complains if number of vals is greater than sum of mandatory and optional specs", meta, ms:
            vals = [1, 2, 3, 4, 5, 6, 7, 8]

            class Yeap(sb.many_item_formatted_spec):
                specs = [1, 2]
                optional_specs = [3, 4]

            with assertRaises(BadSpecValue, "The value is a list with the wrong number of items"):
                Yeap().validate_split(vals, ms.dividers, meta, ms.val)

    describe "split":
        it "sets default dividers to colon and vals to the val if already a list", spec, meta:
            vals = [1, 2, 3, 4]
            result = spec.split(meta, vals)
            assert result == (vals, [":", ":", ":"])

        it "complains if val is a dict without only one item", spec, meta:
            with assertRaises(BadSpecValue, "Value as a dict must only be one item"):
                spec.split(meta, {})

            with assertRaises(BadSpecValue, "Value as a dict must only be one item"):
                spec.split(meta, {1: 2, 3: 4})

        it "sets vals to the first key and val and dividers to a colon if val is a one item dict", spec, meta:
            result = spec.split(meta, {1: 2})
            assert result == ((1, 2), [":"])

        it "sets vals to a list with the val and dividers to nothing if not a list, string or dict", spec, meta:
            val = mock.Mock(name="value")
            result = spec.split(meta, val)
            assert result == ([val], [])

        describe "if val is a string":
            it "sets vals to the one val if no seperators specified", meta:

                class Yeap(sb.many_item_formatted_spec):
                    seperators = None

                assert Yeap().split(meta, "hello") == (["hello"], [None])

            it "splits by the available seperators and accumulates both", meta:

                class Yeap(sb.many_item_formatted_spec):
                    seperators = ":/="

                val = "hello:there/what_ya:doing=huh?"
                expected_val = ["hello", "there/what_ya", "doing", "huh?"]
                expected_dividers = [":", ":", "="]
                assert Yeap().split(meta, val) == (expected_val, expected_dividers)
