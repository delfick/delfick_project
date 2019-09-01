# coding: spec

from input_algorithms.errors import BadSpec, BadSpecValue, DeprecatedKey, BadSpecDefinition
from input_algorithms.spec_base import Spec, NotSpecified
from input_algorithms.validators import Validator
from input_algorithms import validators as va

from tests.helpers import TestCase

from noseOfYeti.tokeniser.support import noy_sup_setUp
import mock

describe TestCase, "Validator":
    before_each:
        self.val = mock.Mock(name="val")
        self.meta = mock.Mock(name="meta")

    it "is a subclass of Spec":
        assert issubclass(Validator, Spec)

    it "returns NotSpecified if not specified":
        self.assertIs(Validator().normalise(self.meta, NotSpecified), NotSpecified)

    it "uses validate if value is specified":
        result = mock.Mock(name="result")
        validate = mock.Mock(name="validate")
        validate.return_value = result

        validator = type("Validator", (Validator, ), {"validate": validate})()
        self.assertIs(validator.normalise(self.meta, self.val), result)
        validate.assert_called_once_with(self.meta, self.val)

describe TestCase, "has_either":
    before_each:
        self.meta = mock.Mock(name="meta")

    it "takes in choices":
        choices = mock.Mock(name="choices")
        validator = va.has_either(choices)
        self.assertIs(validator.choices, choices)

    it "complains if none of the values are satisfied":
        choices = ["one", "two"]
        with self.fuzzyAssertRaisesError(BadSpecValue, "Need to specify atleast one of the required keys", meta=self.meta, choices=choices):
            va.has_either(choices).normalise(self.meta, {})

        with self.fuzzyAssertRaisesError(BadSpecValue, "Need to specify atleast one of the required keys", meta=self.meta, choices=choices):
            va.has_either(choices).normalise(self.meta, {"one": NotSpecified})

    it "Lets the val through if it has atleast one choice":
        val = {"one": 1}
        self.assertEqual(va.has_either(["one", "two"]).normalise(self.meta, val), val)

describe TestCase, "has_only_one_of":
    before_each:
        self.meta = mock.Mock(name="meta")

    it "takes in choices":
        choices = ["one", "two"]
        validator = va.has_only_one_of(choices)
        self.assertIs(validator.choices, choices)

    it "ensures choices is specified":
        choices = []
        with self.fuzzyAssertRaisesError(BadSpecDefinition, "Must specify atleast one choice", got=choices):
            validator = va.has_only_one_of(choices)

    it "complains if none of the values are satisfied":
        choices = ["one", "two"]
        with self.fuzzyAssertRaisesError(BadSpecValue, "Can only specify exactly one of the available choices", meta=self.meta, choices=choices):
            va.has_only_one_of(choices).normalise(self.meta, {})

        with self.fuzzyAssertRaisesError(BadSpecValue, "Can only specify exactly one of the available choices", meta=self.meta, choices=choices):
            va.has_only_one_of(choices).normalise(self.meta, {"one": NotSpecified})

    it "Lets the val through if it has atleast one choice":
        val = {"one": 1}
        self.assertEqual(va.has_only_one_of(["one", "two"]).normalise(self.meta, val), val)

    it "complains if more than one of the values are specified":
        val = {"one": 1, "two": 2}
        choices = ["one", "two"]
        with self.fuzzyAssertRaisesError(BadSpecValue, "Can only specify exactly one of the available choices", meta=self.meta, choices=choices):
            self.assertEqual(va.has_only_one_of(choices).normalise(self.meta, val), val)

describe TestCase, "either_keys":
    before_each:
        self.meta = mock.Mock(name="meta")

    it "takes in choices as positional arguments":
        choice1 = [mock.Mock(name="choice1")]
        choice2 = [mock.Mock(name="choice2")]
        validator = va.either_keys(choice1, choice2)
        self.assertEqual(validator.choices, (choice1, choice2))

    it "complains if the value is not a dictionary":
        for val in (None, 0, 1, "", "a", [], [1], lambda: 1):
            with self.fuzzyAssertRaisesError(BadSpecValue, "Expected a dictionary"):
                va.either_keys().normalise(self.meta, val)

    it "complains if any choice has a common key":
        with self.fuzzyAssertRaisesError(BadSpecDefinition, "Found common keys in the choices", common=sorted(["two", "three"])):
            va.either_keys(["one", "two"], ["two", "three"], ["three", "four"])

    it "complains if any choice is not a list":
        for val in (None, NotSpecified, 0, 1, "", "1", {}, {1:1}, lambda: 1):
            with self.fuzzyAssertRaisesError(BadSpecDefinition, "Each choice must be a list", got=val):
                va.either_keys(["one", "two"], val)

    it "complains if some of the keys in the group aren't in the val":
        with self.fuzzyAssertRaisesError(BadSpecValue, "Missing keys from this group", group=["one", "two"], found=["one"], missing=["two"]):
            va.either_keys(["one", "two"]).normalise(self.meta, {"one": 1})

    it "can associate with a group if multiple are defined and know keys are missing":
        with self.fuzzyAssertRaisesError(BadSpecValue, "Missing keys from this group", group=["one", "two"], found=["one"], missing=["two"]):
            va.either_keys(["one", "two"], ["three", "four"]).normalise(self.meta, {"one": 1})

    it "can know if value associates with multiple groups":
        with self.fuzzyAssertRaisesError(BadSpecValue, "Value associates with multiple groups", associates=[["one", "two"], ["three", "four"]], got={"three": 3, "one": 1}):
            va.either_keys(["one", "two"], ["three", "four"]).normalise(self.meta, {"one": 1, "three": 3})

    it "can understand when it has fulfilled a group and has invalid keys":
        with self.fuzzyAssertRaisesError(BadSpecValue, "Value associates with a group but has keys from other groups", associates_with=["three", "four"], invalid=["one"]):
            va.either_keys(["one", "two"], ["three", "four"]).normalise(self.meta, {"one": 1, "three": 3, "four": 4})

    it "knows when val associates with no groups":
        with self.fuzzyAssertRaisesError(BadSpecValue, "Value associates with no groups", choices=(["one", "two"], ["three", "four"]), val={"five": 5}):
            va.either_keys(["one", "two"], ["three", "four"]).normalise(self.meta, {"five": 5})

    it "can successfully return the val if it perfectly associates with a group and no other":
        val1 = {"three": 3, "four": 4}
        val2 = {"three": 3, "four": 4, "five": 5}
        res1 = va.either_keys(["one", "two"], ["three", "four"]).normalise(self.meta, val1)
        res2 = va.either_keys(["one", "two"], ["three", "four"]).normalise(self.meta, val2)

        self.assertEqual(res1, val1)
        self.assertEqual(res2, val2)

describe TestCase, "no_whitesapce":
    before_each:
        self.meta = mock.Mock(name="meta")

    it "Sets up a whitespace regex":
        fake_compile = mock.Mock(name="fake_compile")
        compiled_regex = mock.Mock(name="compiled_regex")

        with mock.patch("re.compile", fake_compile):
            fake_compile.return_value = compiled_regex
            validator = va.no_whitespace()
            self.assertIs(validator.regex, compiled_regex)

        fake_compile.assert_called_once_with("\s+")

    it "has a regex that finds whitespace":
        validator = va.no_whitespace()
        assert validator.regex.search("  \t\n")
        assert validator.regex.search("\t\n")
        assert validator.regex.search("\n")
        assert validator.regex.search("\n ")
        assert not validator.regex.match("d")

    it "complains if the value has whitespace":
        val = "adf "
        with self.fuzzyAssertRaisesError(BadSpecValue, "Expected no whitespace", meta=self.meta, val=val):
            va.no_whitespace().normalise(self.meta, val)

    it "lets through values that don't have whitespace":
        self.assertEqual(va.no_whitespace().normalise(self.meta, "asdf"), "asdf")

describe TestCase, "no_dots":
    before_each:
        self.meta = mock.Mock(name="meta")

    it "takes in a reason":
        reason = mock.Mock(name="reason")
        self.assertIs(va.no_dots().reason, None)
        self.assertIs(va.no_dots(reason=reason).reason, reason)

    it "lets the value through if it has no dot":
        val = "no dots here"
        self.assertEqual(va.no_dots().normalise(self.meta, val), val)

    describe "When there is a dot":
        it "uses the provided reason when complaining":
            val = "a.dot.in.this.one"
            reason = mock.Mock(name="reason")
            with self.fuzzyAssertRaisesError(BadSpecValue, reason, meta=self.meta, val=val):
                va.no_dots(reason).normalise(self.meta, val)

        it "defaults the reason when no reason is provided":
            val = "a.dot"
            with self.fuzzyAssertRaisesError(BadSpecValue, "Expected no dots", meta=self.meta, val=val):
                va.no_dots().normalise(self.meta, val)

describe TestCase, "regexed":
    before_each:
        self.meta = mock.Mock(name="meta")

    it "takes in regexes which it will compile":
        regex1 = mock.Mock(name="regex1")
        regex2 = mock.Mock(name="regex2")
        regex3 = mock.Mock(name="regex3")
        regex4 = mock.Mock(name="regex4")
        compiled_regex1 = mock.Mock(name="compiled_regex1")
        compiled_regex2 = mock.Mock(name="compiled_regex2")
        compiled_regex3 = mock.Mock(name="compiled_regex3")
        compiled_regex4 = mock.Mock(name="compiled_regex4")

        matched = {
              regex1: compiled_regex1, regex2: compiled_regex2
            , regex3: compiled_regex3, regex4: compiled_regex4
            }

        fake_compile = mock.Mock(name="compile")
        fake_compile.side_effect = lambda reg: matched[reg]
        with mock.patch("re.compile", fake_compile):
            validator = va.regexed(regex1, regex2, regex3, regex4)
            self.assertEqual(
                  validator.regexes
                , [ (regex1, compiled_regex1)
                  , (regex2, compiled_regex2)
                  , (regex3, compiled_regex3)
                  , (regex4, compiled_regex4)
                  ]
                )

    it "returns the value if it matches all the regexes":
        self.assertEqual(va.regexed("[a-z]+", "asdf", "a.+").normalise(self.meta, "asdf"), "asdf")

    it "complains if the value doesn't match any of the regexes":
        val = "meh"
        with self.fuzzyAssertRaisesError(BadSpecValue, "Expected value to match regex, it didn't", spec="blah", meta=self.meta, val=val):
            va.regexed("meh", "m.+", "blah", "other").normalise(self.meta, val)

describe TestCase, "deprecated_key":
    before_each:
        self.meta = mock.Mock(name="meta")

    it "takes in key and a reason":
        key = mock.Mock(name="key")
        reason = mock.Mock(name="reason")
        dk = va.deprecated_key(key, reason)
        self.assertIs(dk.key, key)
        self.assertIs(dk.reason, reason)

    it "complains if the key is in the value":
        key = mock.Mock(name="key")
        reason = mock.Mock(name="reason")
        with self.fuzzyAssertRaisesError(DeprecatedKey, key=key, reason=reason):
            va.deprecated_key(key, reason).normalise(self.meta, {key: 1})

    it "doesn't complain if the key is not in the value":
        key = mock.Mock(name="key")
        reason = mock.Mock(name="reason")
        va.deprecated_key(key, reason).normalise(self.meta, {})
        assert True

    it "doesn't fail if the val is not iterable":
        key = mock.Mock(name="key")
        reason = mock.Mock(name="reason")
        va.deprecated_key(key, reason).normalise(self.meta, None)
        assert True

describe TestCase, "choice":
    before_each:
        self.meta = mock.Mock(name="meta")

    it "complains if the val is not one of the choices":
        with self.fuzzyAssertRaisesError(BadSpecValue, "Expected the value to be one of the valid choices", got=4, choices=(1, 2, 3), meta=self.meta):
            va.choice(1, 2, 3).normalise(self.meta, 4)

    it "returns the val if it's one of the choices":
        self.assertIs(va.choice(1, 2, 3, 4).normalise(self.meta, 4), 4)

