# coding: spec

from unittest import mock

import pytest

from delfick_project.addons import Result
from delfick_project.errors_pytest import assertRaises
from delfick_project.norms import BadSpecValue, Meta

describe "Result":

    @pytest.fixture()
    def meta(self):
        return Meta.empty()

    @pytest.fixture()
    def spec(self):
        return Result.FieldSpec()

    @pytest.fixture()
    def with_normalise(self):
        return mock.Mock(name="with_normalise", spec=["normalise"])

    @pytest.fixture()
    def without_normalise(self):
        return mock.Mock(name="with_normalise", spec=[])

    it "makes sure the keys of specs are tuples of int and tuple", meta, spec, with_normalise:
        res = spec.normalise(meta, {"specs": {"blah": with_normalise}})
        assert res.specs == {("blah",): with_normalise}

        res = spec.normalise(meta, {"specs": {"blah": with_normalise}})
        assert res.specs == {("blah",): with_normalise}

        res = spec.normalise(meta, {"specs": {("blah", "meh"): with_normalise}})
        assert res.specs == {("blah", "meh"): with_normalise}

    it "makes sure the value of specs has a normalise method", meta, spec, without_normalise:
        error1 = BadSpecValue(
            "Value is missing required properties",
            meta=meta.at("specs").at("blah"),
            missing=["normalise"],
            required=("normalise",),
        )
        error2 = BadSpecValue(meta=meta.at("specs"), _errors=[error1])
        with assertRaises(BadSpecValue, _errors=[error2]):
            spec.normalise(meta, {"specs": {"blah": without_normalise}})

    it "makes sure extras is a list of string to tuple of strings", meta, spec:
        res = spec.normalise(meta, {"extras": [("one", "two")]})
        assert res.extras == [("one", ("two",))]

        res = spec.normalise(meta, {"extras": [("three", ["four"])]})
        assert res.extras == [("three", ("four",))]
