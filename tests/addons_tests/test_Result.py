# coding: spec

from input_algorithms.errors import BadSpecValue
from option_merge_addons import Result

from tests.helpers import TestCase

from noseOfYeti.tokeniser.support import noy_sup_setUp
from input_algorithms.meta import Meta
import mock

describe TestCase, "Result":
    before_each:
        self.with_normalise = mock.Mock(name="with_normalise", spec=["normalise"])
        self.without_normalise = mock.Mock(name="with_normalise", spec=[])
        self.meta = Meta({}, [])
        self.spec = Result.FieldSpec()

    it "makes sure the keys of specs are tuples of int and tuple":
        res = self.spec.normalise(self.meta, {"specs": {(0, "blah"): self.with_normalise}})
        self.assertEqual(res.specs, {(0, ("blah", )): self.with_normalise})

        res = self.spec.normalise(self.meta, {"specs": {"blah": self.with_normalise}})
        self.assertEqual(res.specs, {(0, ("blah", )): self.with_normalise})

        res = self.spec.normalise(self.meta, {"specs": {("blah", ): self.with_normalise}})
        self.assertEqual(res.specs, {(0, ("blah", )): self.with_normalise})

    it "makes sure the value of specs has a normalise method":
        error1 = BadSpecValue("Value is missing required properties", meta=self.meta.at("specs").at((0, "blah")), missing=["normalise"], required=('normalise', ))
        error2 = BadSpecValue(meta=self.meta.at("specs"), _errors=[error1])
        with self.fuzzyAssertRaisesError(BadSpecValue, _errors=[error2]):
            self.spec.normalise(self.meta, {"specs": {(0, "blah"): self.without_normalise}})

    it "makes sure extras is a list of string to tuple of strings":
        res = self.spec.normalise(self.meta, {"extras": [("one", "two")]})
        self.assertEqual(res.extras, [("one", ("two", ))])

        res = self.spec.normalise(self.meta, {"extras": [("three", ["four"])]})
        self.assertEqual(res.extras, [("three", ("four", ))])
