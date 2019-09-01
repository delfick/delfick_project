# coding: spec

from tests.helpers import TestCase

from input_algorithms.errors import BadSpecValue
from input_algorithms.dictobj import dictobj
from input_algorithms import spec_base as sb
from input_algorithms.meta import Meta

describe TestCase, "Selection":
    describe "plain dictobj with lists":
        it "works with plain fields":
            class Original(dictobj):
                fields = ["one", "two", "three"]

            Changed = Original.selection("Changed", ["one", "three"])
            changed = Changed(one=1, three=3)
            assert not hasattr(changed, "two")
            self.assertEqual(changed.one, 1)
            self.assertEqual(changed.three, 3)

            self.assertEqual(sorted(changed.fields), sorted(["one", "three"]))

        it "works with fields that have defaults":
            class Original(dictobj):
                fields = [("one", 2), "two", "three"]

            Changed = Original.selection("Changed", ["one", "two"])
            changed = Changed(two=5)
            assert not hasattr(changed, "three")
            self.assertEqual(changed.one, 2)
            self.assertEqual(changed.two, 5)

            self.assertEqual(sorted(str(t) for t in changed.fields), sorted([str(t) for t in (("one", 2), "two")]))

        it "works for fields that are dictionaries to help messages":
            class Original(dictobj):
                fields = {"one": "one!", ("two", 6): "two", "three": "three?"}

            Changed = Original.selection("Changed", ["one", "two"])
            changed = Changed(one=1)
            assert not hasattr(changed, "three")
            self.assertEqual(changed.one, 1)
            self.assertEqual(changed.two, 6)

            self.assertEqual(changed.fields, {"one": "one!", ("two", 6): "two"})

    describe "with dictobj.Spec":
        it "works":
            class Original(dictobj.Spec):
                one = dictobj.Field(sb.string_spec)
                two = dictobj.Field(sb.integer_spec, default=3)
                three = dictobj.Field(sb.string_spec, help="three")
                four = dictobj.Field(sb.any_spec)

            Changed = Original.selection("Changed", ["one", "three", "two"])
            changed = Changed.FieldSpec().empty_normalise(one="1", three="3")

            assert not hasattr(changed, "four")
            self.assertEqual(changed.one, "1")
            self.assertEqual(changed.two, 3)
            self.assertEqual(changed.three, "3")

        it "allows optional values":
            class Original(dictobj.Spec):
                one = dictobj.Field(sb.string_spec)
                two = dictobj.Field(sb.integer_spec, default=3)
                three = dictobj.Field(sb.string_spec, help="three")
                four = dictobj.Field(sb.any_spec)

            Changed = Original.selection("Changed", ["one", "three", "two"], optional=["three", "two"])
            changed = Changed.FieldSpec().empty_normalise(one="1")

            assert not hasattr(changed, "four")
            self.assertEqual(changed.one, "1")
            self.assertEqual(changed.two, 3)
            self.assertEqual(changed.three, sb.NotSpecified)

        it "allows setting all values to be optional":
            class Original(dictobj.Spec):
                one = dictobj.Field(sb.string_spec)
                two = dictobj.Field(sb.integer_spec)
                three = dictobj.Field(sb.string_spec)
                four = dictobj.Field(sb.any_spec)

            Changed = Original.selection("Changed", ["one", "two"], all_optional=True)
            changed = Changed.FieldSpec().empty_normalise()

            assert not hasattr(changed, "three")
            assert not hasattr(changed, "four")
            self.assertEqual(changed.one, sb.NotSpecified)
            self.assertEqual(changed.two, sb.NotSpecified)

        it "allows setting all values to be required":
            class Original(dictobj.Spec):
                one = dictobj.Field(sb.string_spec)
                two = dictobj.Field(sb.integer_spec)
                three = dictobj.Field(sb.string_spec)
                four = dictobj.Field(sb.any_spec)

            Changed = Original.selection("Changed", ["one", "two"], all_required=True)

            m = Meta.empty()
            error1 = BadSpecValue("Expected a value but got none", meta=m.at("two"))
            error2 = BadSpecValue("Expected a value but got none", meta=m.at("one"))

            with self.fuzzyAssertRaisesError(BadSpecValue, _errors=[error1, error2]):
                changed = Changed.FieldSpec().normalise(m, {})

        it "can override all_required with optional":
            class Original(dictobj.Spec):
                one = dictobj.Field(sb.string_spec)
                two = dictobj.Field(sb.integer_spec)
                three = dictobj.Field(sb.string_spec)
                four = dictobj.Field(sb.any_spec)

            Changed = Original.selection("Changed", ["one", "two"], all_required=True, optional=["two"])

            m = Meta.empty()
            error2 = BadSpecValue("Expected a value but got none", meta=m.at("one"))

            with self.fuzzyAssertRaisesError(BadSpecValue, _errors=[error2]):
                changed = Changed.FieldSpec().normalise(m, {})

        it "can override all_optional with required":
            class Original(dictobj.Spec):
                one = dictobj.Field(sb.string_spec)
                two = dictobj.Field(sb.integer_spec)
                three = dictobj.Field(sb.string_spec)
                four = dictobj.Field(sb.any_spec)

            Changed = Original.selection("Changed", ["one", "two"], all_optional=True, required=["two"])

            m = Meta.empty()
            error1 = BadSpecValue("Expected a value but got none", meta=m.at("two"))

            with self.fuzzyAssertRaisesError(BadSpecValue, _errors=[error1]):
                changed = Changed.FieldSpec().normalise(m, {})

