# coding: spec

import uuid
from unittest import mock

import pytest

from delfick_project.errors_pytest import assertRaises
from delfick_project.norms import (
    BadSpecDefinition,
    BadSpecValue,
    DeprecatedKey,
    Meta,
    Validator,
    sb,
    va,
)


@pytest.fixture()
def meta():
    return Meta.empty()


describe "Validator":
    it "is a subclass of Spec":
        assert issubclass(Validator, sb.Spec)

    it "returns sb.NotSpecified if not specified", meta:
        assert Validator().normalise(meta, sb.NotSpecified) is sb.NotSpecified

    it "uses validate if value is specified", meta:
        val = mock.Mock(name="val")
        result = mock.Mock(name="result")
        validate = mock.Mock(name="validate")
        validate.return_value = result

        validator = type("Validator", (Validator,), {"validate": validate})()
        assert validator.normalise(meta, val) is result
        validate.assert_called_once_with(meta, val)

describe "has_either":
    it "takes in choices":
        choices = mock.Mock(name="choices")
        validator = va.has_either(choices)
        assert validator.choices is choices

    it "complains if none of the values are satisfied", meta:
        choices = ["one", "two"]
        with assertRaises(
            BadSpecValue,
            "Need to specify atleast one of the required keys",
            meta=meta,
            choices=choices,
        ):
            va.has_either(choices).normalise(meta, {})

        with assertRaises(
            BadSpecValue,
            "Need to specify atleast one of the required keys",
            meta=meta,
            choices=choices,
        ):
            va.has_either(choices).normalise(meta, {"one": sb.NotSpecified})

    it "Lets the val through if it has atleast one choice", meta:
        val = {"one": 1}
        assert va.has_either(["one", "two"]).normalise(meta, val) == val

describe "has_only_one_of":
    it "takes in choices":
        choices = ["one", "two"]
        validator = va.has_only_one_of(choices)
        assert validator.choices is choices

    it "ensures choices is specified":
        choices = []
        with assertRaises(BadSpecDefinition, "Must specify atleast one choice", got=choices):
            va.has_only_one_of(choices)

    it "complains if none of the values are satisfied", meta:
        choices = ["one", "two"]
        with assertRaises(
            BadSpecValue,
            "Can only specify exactly one of the available choices",
            meta=meta,
            choices=choices,
        ):
            va.has_only_one_of(choices).normalise(meta, {})

        with assertRaises(
            BadSpecValue,
            "Can only specify exactly one of the available choices",
            meta=meta,
            choices=choices,
        ):
            va.has_only_one_of(choices).normalise(meta, {"one": sb.NotSpecified})

    it "Lets the val through if it has atleast one choice", meta:
        val = {"one": 1}
        assert va.has_only_one_of(["one", "two"]).normalise(meta, val) == val

    it "complains if more than one of the values are specified", meta:
        val = {"one": 1, "two": 2}
        choices = ["one", "two"]
        with assertRaises(
            BadSpecValue,
            "Can only specify exactly one of the available choices",
            meta=meta,
            choices=choices,
        ):
            assert va.has_only_one_of(choices).normalise(meta, val) == val

describe "either_keys":
    it "takes in choices as positional arguments":
        choice1 = [mock.Mock(name="choice1")]
        choice2 = [mock.Mock(name="choice2")]
        validator = va.either_keys(choice1, choice2)
        assert validator.choices == (choice1, choice2)

    it "complains if the value is not a dictionary", meta:
        for val in (None, 0, 1, "", "a", [], [1], lambda: 1):
            with assertRaises(BadSpecValue, "Expected a dictionary"):
                va.either_keys().normalise(meta, val)

    it "complains if any choice has a common key":
        with assertRaises(
            BadSpecDefinition, "Found common keys in the choices", common=sorted(["two", "three"])
        ):
            va.either_keys(["one", "two"], ["two", "three"], ["three", "four"])

    it "complains if any choice is not a list":
        for val in (None, sb.NotSpecified, 0, 1, "", "1", {}, {1: 1}, lambda: 1):
            with assertRaises(BadSpecDefinition, "Each choice must be a list", got=val):
                va.either_keys(["one", "two"], val)

    it "complains if some of the keys in the group aren't in the val", meta:
        with assertRaises(
            BadSpecValue,
            "Missing keys from this group",
            group=["one", "two"],
            found=["one"],
            missing=["two"],
        ):
            va.either_keys(["one", "two"]).normalise(meta, {"one": 1})

    it "can associate with a group if multiple are defined and know keys are missing", meta:
        with assertRaises(
            BadSpecValue,
            "Missing keys from this group",
            group=["one", "two"],
            found=["one"],
            missing=["two"],
        ):
            va.either_keys(["one", "two"], ["three", "four"]).normalise(meta, {"one": 1})

    it "can know if value associates with multiple groups", meta:
        with assertRaises(
            BadSpecValue,
            "Value associates with multiple groups",
            associates=[["one", "two"], ["three", "four"]],
            got={"three": 3, "one": 1},
        ):
            va.either_keys(["one", "two"], ["three", "four"]).normalise(
                meta, {"one": 1, "three": 3}
            )

    it "can understand when it has fulfilled a group and has invalid keys", meta:
        with assertRaises(
            BadSpecValue,
            "Value associates with a group but has keys from other groups",
            associates_with=["three", "four"],
            invalid=["one"],
        ):
            va.either_keys(["one", "two"], ["three", "four"]).normalise(
                meta, {"one": 1, "three": 3, "four": 4}
            )

    it "knows when val associates with no groups", meta:
        with assertRaises(
            BadSpecValue,
            "Value associates with no groups",
            choices=(["one", "two"], ["three", "four"]),
            val={"five": 5},
        ):
            va.either_keys(["one", "two"], ["three", "four"]).normalise(meta, {"five": 5})

    it "can successfully return the val if it perfectly associates with a group and no other", meta:
        val1 = {"three": 3, "four": 4}
        val2 = {"three": 3, "four": 4, "five": 5}
        res1 = va.either_keys(["one", "two"], ["three", "four"]).normalise(meta, val1)
        res2 = va.either_keys(["one", "two"], ["three", "four"]).normalise(meta, val2)

        assert res1 == val1
        assert res2 == val2

describe "no_whitesapce":
    it "Sets up a whitespace regex":
        fake_compile = mock.Mock(name="fake_compile")
        compiled_regex = mock.Mock(name="compiled_regex")

        with mock.patch("re.compile", fake_compile):
            fake_compile.return_value = compiled_regex
            validator = va.no_whitespace()
            assert validator.regex is compiled_regex

        fake_compile.assert_called_once_with(r"\s+")

    it "has a regex that finds whitespace":
        validator = va.no_whitespace()
        assert validator.regex.search("  \t\n")
        assert validator.regex.search("\t\n")
        assert validator.regex.search("\n")
        assert validator.regex.search("\n ")
        assert not validator.regex.match("d")

    it "complains if the value has whitespace", meta:
        val = "adf "
        with assertRaises(BadSpecValue, "Expected no whitespace", meta=meta, val=val):
            va.no_whitespace().normalise(meta, val)

    it "lets through values that don't have whitespace", meta:
        assert va.no_whitespace().normalise(meta, "asdf") == "asdf"

describe "no_dots":
    it "takes in a reason":
        reason = mock.Mock(name="reason")
        assert va.no_dots().reason is None
        assert va.no_dots(reason=reason).reason is reason

    it "lets the value through if it has no dot", meta:
        val = "no dots here"
        assert va.no_dots().normalise(meta, val) == val

    describe "When there is a dot":
        it "uses the provided reason when complaining", meta:
            val = "a.dot.in.this.one"
            reason = str(uuid.uuid1())
            with assertRaises(BadSpecValue, reason, meta=meta, val=val):
                va.no_dots(reason).normalise(meta, val)

        it "defaults the reason when no reason is provided", meta:
            val = "a.dot"
            with assertRaises(BadSpecValue, "Expected no dots", meta=meta, val=val):
                va.no_dots().normalise(meta, val)

describe "regexed":
    it "takes in regexes which it will compile", meta:
        regex1 = mock.Mock(name="regex1")
        regex2 = mock.Mock(name="regex2")
        regex3 = mock.Mock(name="regex3")
        regex4 = mock.Mock(name="regex4")
        compiled_regex1 = mock.Mock(name="compiled_regex1")
        compiled_regex2 = mock.Mock(name="compiled_regex2")
        compiled_regex3 = mock.Mock(name="compiled_regex3")
        compiled_regex4 = mock.Mock(name="compiled_regex4")

        matched = {
            regex1: compiled_regex1,
            regex2: compiled_regex2,
            regex3: compiled_regex3,
            regex4: compiled_regex4,
        }

        fake_compile = mock.Mock(name="compile")
        fake_compile.side_effect = lambda reg: matched[reg]
        with mock.patch("re.compile", fake_compile):
            validator = va.regexed(regex1, regex2, regex3, regex4)
            assert validator.regexes == [
                (regex1, compiled_regex1),
                (regex2, compiled_regex2),
                (regex3, compiled_regex3),
                (regex4, compiled_regex4),
            ]

    it "returns the value if it matches all the regexes", meta:
        assert va.regexed("[a-z]+", "asdf", "a.+").normalise(meta, "asdf") == "asdf"

    it "complains if the value doesn't match any of the regexes", meta:
        val = "meh"
        with assertRaises(
            BadSpecValue,
            "Expected value to match regex, it didn't",
            spec="blah",
            meta=meta,
            val=val,
        ):
            va.regexed("meh", "m.+", "blah", "other").normalise(meta, val)

describe "deprecated_key":
    it "takes in key and a reason":
        key = mock.Mock(name="key")
        reason = mock.Mock(name="reason")
        dk = va.deprecated_key(key, reason)
        assert dk.key is key
        assert dk.reason is reason

    it "complains if the key is in the value", meta:
        key = mock.Mock(name="key")
        reason = mock.Mock(name="reason")
        with assertRaises(DeprecatedKey, key=key, reason=reason):
            va.deprecated_key(key, reason).normalise(meta, {key: 1})

    it "doesn't complain if the key is not in the value", meta:
        key = mock.Mock(name="key")
        reason = mock.Mock(name="reason")
        va.deprecated_key(key, reason).normalise(meta, {})
        assert True

    it "doesn't fail if the val is not iterable", meta:
        key = mock.Mock(name="key")
        reason = mock.Mock(name="reason")
        va.deprecated_key(key, reason).normalise(meta, None)
        assert True

describe "choice":
    it "complains if the val is not one of the choices", meta:
        with assertRaises(
            BadSpecValue,
            "Expected the value to be one of the valid choices",
            got=4,
            choices=(1, 2, 3),
            meta=meta,
        ):
            va.choice(1, 2, 3).normalise(meta, 4)

    it "returns the val if it's one of the choices", meta:
        assert va.choice(1, 2, 3, 4).normalise(meta, 4) == 4
