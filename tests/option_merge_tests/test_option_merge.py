# coding: spec

from delfick_project.option_merge import (
    NotFound,
    Converter,
    MergedOptions,
    ConverterProperty,
    AttributesConverter,
    KeyValuePairsConverter,
)
from delfick_project.option_merge.storage import Storage

from delfick_project.errors_pytest import assertRaises

from unittest import mock
import pytest


@pytest.fixture()
def merged():
    return MergedOptions()


describe "MergedOptions":
    it "has prefix and storage":
        storage = mock.Mock(name="storage")
        dot_joiner = mock.Mock(name="dot_joiner")
        prefix_list = mock.Mock(name="prefix_list")
        prefix_string = mock.Mock(name="prefix_string")

        dot_joiner.return_value = prefix_string
        with mock.patch("delfick_project.option_merge.merge.dot_joiner", dot_joiner):
            merged = MergedOptions(prefix=prefix_list, storage=storage)

        assert merged.storage is storage
        assert merged.prefix_list is prefix_list
        assert merged.prefix_string is prefix_string

        merged = MergedOptions()
        assert merged.prefix_list == []
        assert merged.prefix_string == ""
        assert type(merged.storage) == Storage

    it "has classmethod for adding options":
        options1 = mock.Mock(name="options1")
        options2 = mock.Mock(name="options2")

        merged = MergedOptions.using(options1, options2, source="somewhere")
        assert merged.storage.data == [([], options2, "somewhere"), ([], options1, "somewhere")]

    it "doesn't infinitely recurse when has self referential information":
        data = MergedOptions.using({"items": {}})
        data["items"] = data
        options2 = MergedOptions.using(data, {"items": data["items"]})
        print(list(options2["items"].items()))
        assert True, "It didn't reach maximum recursion depth"

    it "doesn't infinitely recurse when has self referential information added afterwards":
        data = MergedOptions.using({"items": {"a": 1}})
        items = data["items"]
        assert items["a"] is 1
        data.update({"items": items})
        assert items["a"] is 1
        assert True, "It didn't reach maximum recursion depth"

    describe "source_for":
        it "works with a single layer of merged option":
            options = MergedOptions()
            options.update({"wat": 1}, source="a")
            options.update({"yeap": {"blah": 3, "meh": 4}}, source="b")
            options.update({"yeap": {"blah": 2}}, source="d")

            assert options.source_for("wat") == ["a"]
            assert options.source_for("yeap.blah") == ["d", "b"]
            assert options.source_for("yeap.meh") == ["b"]

        it "works with layered merged options":
            options = MergedOptions()
            options.update({"wat": 1}, source="a")
            options.update({"yeap": {"blah": 3, "meh": 4}}, source="b")
            options.update({"yeap": {"blah": 2}}, source="d")

            options2 = MergedOptions()
            options2.update({"thing": {"other": 10}}, source="e")

            options3 = MergedOptions.using(options)
            options3["place"] = options2

            assert options3.source_for("wat") == ["a"]
            assert options3.source_for("yeap.blah") == ["d", "b"]
            assert options3.source_for("yeap.meh") == ["b"]
            assert options3.source_for("place.thing.other") == ["e"]

        it "works if one of the storage data is a prefixed merged options":
            options = MergedOptions()
            options.update({"wat": 1}, source="a")
            options.update({"yeap": {"blah": 3, "meh": 4}}, source="b")
            options.update({"yeap": {"blah": 2}}, source="d")

            options2 = MergedOptions()
            options2.update({"thing": {"other": 10}}, source="e")

            options3 = MergedOptions.using(options)
            options3["place"] = options2["thing"]

            assert options3.source_for("wat") == ["a"]
            assert options3.source_for("yeap.blah") == ["d", "b"]
            assert options3.source_for("yeap.meh") == ["b"]

            assert options2.source_for("thing.other") == ["e"]
            assert options3.source_for("place.other") == ["e"]

    describe "Adding more options":

        it "has method for adding more options":
            options1 = mock.Mock(name="options1")
            options2 = mock.Mock(name="options2")

            merged = MergedOptions()
            merged.update(options1)
            assert merged.storage.data == [([], options1, None)]

            merged.update(options2)
            assert merged.storage.data == [([], options2, None), ([], options1, None)]

        it "Works when there is a prefix":
            options = MergedOptions.using({"a": {"b": 1, "c": 2}})
            a_opt = options["a"]
            assert sorted(a_opt.items()) == sorted([("b", 1), ("c", 2)])

            a_opt.update({"c": 3})
            assert a_opt["c"] == 3

    describe "testing inclusion":
        it "says yes if a key is in the option merge":
            merge = MergedOptions.using(
                {"one": "two", "three": {"four": "five"}}, {"three": 3, "nine.ten": {"eleven": 1}}
            )
            assert "one" in merge
            assert "three.four" in merge
            assert "three" in merge
            assert "nine.ten.eleven" in merge
            del merge["three"]
            assert "three.four" in merge

            assert "three.seven" not in merge
            assert "eight" not in merge

        it "works with lists":
            merge = MergedOptions.using(
                {"one": "two", "three": {"four": "five"}}, {"three": 3, "nine.ten": {"eleven": 1}}
            )
            assert ["one"] in merge
            assert ["three", "four"] in merge
            assert ["three"] in merge
            del merge["three"]
            assert ["three", "four"] in merge

            assert ["three", "seven"] not in merge
            assert ["eight"] not in merge

            assert ["nine.ten", "eleven"] in merge
            assert ["nine", "ten", "eleven"] not in merge

        it "doesn't convert when testing membership":

            class Other(object):
                pass

            other = Other()
            d1 = mock.Mock(name="d1", spec=[])
            convert = mock.Mock(name="convert")
            convert.return_value = other

            merge = MergedOptions.using({"a": d1})
            converter = Converter(convert, convert_path="a")
            merge.add_converter(converter)
            merge.converters.activate()

            assert merge.storage.data == [([], {"a": d1}, None)]
            assert "a" in merge
            assert convert.mock_calls == []
            assert merge.storage.data == [([], {"a": d1}, None)]

            assert merge["a"] is other
            convert.assert_called_once_with("a", d1)
            assert merge["a"] is other
            assert len(convert.mock_calls) == 1

    describe "Getting an item":
        it "raises a KeyError if the key doesn't exist", merged:
            with assertRaises(KeyError, "blah"):
                merged["blah"]

        it "gets the first value for that key if it exists", merged:
            val1 = mock.Mock(name="val1")
            val2 = mock.Mock(name="val2")
            fake_values_for = mock.Mock(name="values_for")
            fake_values_for.return_value = [(val1, False), (val2, False)]
            with mock.patch.object(merged, "values_for", fake_values_for):
                assert merged["blah"] is val1
            fake_values_for.assert_called_once_with("blah", ignore_converters=False)

        it "works with the get method", merged:
            val1 = mock.Mock(name="val1")
            val2 = mock.Mock(name="val2")
            fake_values_for = mock.Mock(name="values_for")
            fake_values_for.return_value = [(val1, False), (val2, False)]
            with mock.patch.object(merged, "values_for", fake_values_for):
                assert merged.get("blah") is val1
            fake_values_for.assert_called_once_with("blah", ignore_converters=False)

        it "works if we get one subtree from a different subtree":
            val1 = mock.Mock(name="val1")
            val2 = mock.Mock(name="val2")
            options = MergedOptions.using({"one": {"two": val1}}, {"one": {"three": val2}})
            assert sorted(options["one"].keys()) == ["three", "two"]
            assert options["one"]["two"] is val1
            assert options["one"]["three"] is val2

        it "works if we get one subtree from a different subtree if subtrees are MergedOptions":
            val1 = mock.Mock(name="val1")
            val2 = mock.Mock(name="val2")
            options = MergedOptions.using(
                {"one": MergedOptions.using({"two": val1})},
                {"one": MergedOptions.using({"three": val2})},
            )
            assert sorted(options["one"].keys()) == ["three", "two"]
            assert options["one"]["two"] is val1
            assert options["one"]["three"] is val2

        it "can get items from inside a converter":
            thing = MergedOptions.using(
                {"opts": MergedOptions.using({"blah": 1, "stuff": 2, "things": [1, 2]})}
            )
            converted_val = {}

            def converter(path, val):
                thing.converters.done(path, converted_val)
                items = dict(val.items())
                assert items == {"blah": 1, "stuff": 2, "things": [1, 2]}
                converted_val.update(items)
                return converted_val

            thing.add_converter(Converter(convert=converter, convert_path=["opts"]))
            thing.converters.activate()
            assert thing["opts"] is converted_val

        it "can return as is if the type is dict like but in dont_prefix":

            class A(dict):
                pass

            class B(A):
                pass

            class C(dict):
                pass

            thing = MergedOptions(dont_prefix=[A])
            a = A()
            b = B()
            c = C()
            thing["one"] = a
            thing["two"] = b
            thing["three"] = c

            assert thing["one"] is a
            assert thing["two"] is b
            assert type(thing["three"]) == MergedOptions

        it "can get items from inside a converter after a level of indirection":
            final = MergedOptions()

            thing = MergedOptions.using(
                {"blah": 1, "stuff": 2, "things": [1, 2]}, converters=final.converters
            )
            other = MergedOptions.using({"tree": 5, "pole": 6}, converters=final.converters)

            final.update({"seven": 7, "eight": 8, "images": {"thing": thing, "other": other}})
            final.update({"two": 2, "three": 3})
            final.update({"images": {"other": {"stuff": 7}}})

            converted_val = {}

            def converter(path, val):
                final.converters.done(path, converted_val)
                items = dict(val.items(ignore_converters=True))
                if path == "images.other":
                    assert items == {"tree": 5, "pole": 6, "stuff": 7}
                else:
                    assert items == {"blah": 1, "stuff": 2, "things": [1, 2]}

                converted_val.update(items)

                everything = MergedOptions.using(
                    path.configuration.root(), converters=final.converters
                )
                if path == "images.other":
                    assert isinstance(everything["images.thing"], dict)
                else:
                    assert isinstance(everything["images.other"], dict)

                return converted_val

            final.add_converter(Converter(convert=converter, convert_path=["images", "other"]))
            final.add_converter(Converter(convert=converter, convert_path=["images", "thing"]))
            final.converters.activate()
            assert final["images.thing"] is converted_val

    describe "Setting an item":
        it "adds to data", merged:
            merged["a"] = 1
            merged["a"] = {"a": "b"}

            assert list(merged["a"].items()) == [("a", "b")]

            merged["a"] = 4
            assert merged["a"] == 4

            del merged["a"]
            del merged["a"]
            assert merged["a"] == 1

    describe "Deleting an item":
        it "only deletes once", merged:
            merged.update({"a": 1})
            merged.update({"a": 2})
            merged["a"] = 3
            assert merged["a"] == 3

            del merged["a"]
            assert merged["a"] == 2

            del merged["a"]
            assert merged["a"] == 1

        it "complains if there is nothing to delete", merged:
            merged["a"] = 3
            assert merged["a"] == 3

            del merged["a"]
            with assertRaises(KeyError, "a"):
                merged["a"]
            with assertRaises(KeyError, "a"):
                del merged["a"]

            merged.update({"b": 1})
            assert merged["b"] == 1
            del merged["b"]
            with assertRaises(KeyError, "b"):
                del merged["b"]

        it "can delete from a nested dict", merged:
            merged.update({"a": 1, "b": {"c": 5}})
            merged.update({"a": {"c": 4}, "b": {"c": 6, "d": 8}})
            merged["a"] = {"c": 5}

            values = list(merged.values_for("b"))
            assert values == [({"c": 6, "d": 8}, False), ({"c": 5}, False)]

            del merged["b"]["c"]
            values = list(merged.values_for("b"))
            assert values == [({"d": 8}, False), ({"c": 5}, False)]

            del merged["b"]["c"]
            values = list(merged.values_for("b"))
            assert values == [({"d": 8}, False), ({}, False)]

        it "can delete dot seperated values", merged:
            merged.update({"a": 1, "b": {"c": 5}})
            merged.update({"a": {"c": 4}, "b": {"c": 6, "d": 8}})
            merged["a"] = {"c": 5}

            values = list(merged.values_for("b"))
            assert values == [({"c": 6, "d": 8}, False), ({"c": 5}, False)]

            del merged["b.c"]
            values = list(merged.values_for("b"))
            assert values == [({"d": 8}, False), ({"c": 5}, False)]

            del merged["b.c"]
            values = list(merged.values_for("b"))
            assert values == [({"d": 8}, False), ({}, False)]

        it "can delete lists", merged:
            merged.update({"a": 1, "b": {"c": 5}})
            merged.update({"a": {"c": 4}, "b": {"c": 6, "d": 8}})
            merged["a"] = {"c": 5}

            values = list(merged.values_for("b"))
            assert values == [({"c": 6, "d": 8}, False), ({"c": 5}, False)]

            del merged[["b", "c"]]
            values = list(merged.values_for("b"))
            assert values == [({"d": 8}, False), ({"c": 5}, False)]

            del merged[["b", "c"]]
            values = list(merged.values_for("b"))
            assert values == [({"d": 8}, False), ({}, False)]

    describe "Getting all values for a key":
        it "finds all the values", merged:
            merged.update({"a": 1, "b": {"c": 5}})
            merged.update({"a": {"c": 4}, "b": 4})
            merged["a"] = {"c": 5}
            values = list(merged.values_for("a"))
            assert values == [({"c": 5}, False), ({"c": 4}, False), (1, False)]

            merged["a"] = 400
            values = list(merged.values_for("a"))
            assert values == [(400, False), ({"c": 5}, False), ({"c": 4}, False), (1, False)]

    describe "Getting keys":
        describe "Getting keys on a mergedOptions":
            it "returns one level of keys", merged:
                merged.update({"a": {"b": {"c": 1}, "d": 5}, "t": 6, "u": {}})
                assert sorted(merged.keys()) == sorted(["a", "t", "u"])

                merged.update({"a": 3, "e": 7})
                assert sorted(merged.keys()) == sorted(["a", "t", "u", "e"])

                merged["h"] = 10
                assert sorted(merged.keys()) == sorted(["a", "t", "u", "e", "h"])

            it "returns one level of keys from prefix", merged:
                prefixed = merged.prefixed("a")
                merged.update({"a": {"b": {"c": 1}, "d": 5}, "t": 6, "u": {}})
                assert sorted(prefixed.keys()) == sorted(["b", "d"])

                merged.update({"a": {"g": 6}, "e": 7})
                assert sorted(prefixed.keys()) == sorted(["g", "b", "d"])

                merged["a"] = {"h": 9}
                assert sorted(prefixed.keys()) == sorted(["h", "g", "b", "d"])

            it "returns keys one level from multi dictionary MergedOptions", merged:
                merged.update({"a": 1, "b": {"c": 9}})
                merged.update({"a": {"c": 4}, "b": 4})
                merged["a"] = {"c": 5, "d": 8}
                merged["a"]["c"] = {"c": 5, "d": 9}
                assert sorted(merged.keys()) == sorted(["a", "b"])

            it "returns empty if there are no keys":
                opts = MergedOptions()
                assert list(opts.keys()) == []

                opts = MergedOptions.using({"items": MergedOptions()})
                assert list(opts["items"].keys()) == []

    describe "Iteration":
        it "just goes through the keys", merged:
            fake_keys = mock.Mock(name="keys")
            fake_keys.side_effect = lambda: iter([1, 2, 3])
            with mock.patch.object(merged, "keys", fake_keys):
                assert list(merged) == [1, 2, 3]

    describe "Length":
        it "Counts the number of keys", merged:
            keys = []
            fake_keys = mock.Mock(name="keys")
            fake_keys.side_effect = lambda: iter(keys)
            with mock.patch.object(merged, "keys", fake_keys):
                assert len(merged) == 0

                keys.append(1)
                assert len(merged) == 1

                keys.extend([2, 3, 4])
                assert len(merged) == 4

    describe "Getting items":
        it "combines everything into one key,value list", merged:
            merged.update({"a": 1, "b": {"c": 9}})
            merged.update({"a": {"c": 4}, "b": 4})
            merged["a"] = {"c": 5, "d": 8}
            assert sorted(merged.items()) == sorted({"b": 4, "a": merged.prefixed("a")}.items())

            del merged["b"]
            assert sorted(merged.items()) == (
                sorted({"b": merged.prefixed("b"), "a": merged.prefixed("a")}.items())
            )
            assert sorted((k, dict(v.items())) for k, v in merged.items()) == sorted(
                {"b": {"c": 9}, "a": {"c": 5, "d": 8}}.items()
            )

            del merged["a.c"]
            assert sorted(merged.items()) == (
                sorted({"b": merged.prefixed("b"), "a": merged.prefixed("a")}.items())
            )
            assert sorted((k, dict(v.items())) for k, v in merged.items()) == sorted(
                {"b": {"c": 9}, "a": {"c": 4, "d": 8}}.items()
            )

        it "returns empty if there are no values":
            opts = MergedOptions()
            assert list(opts.items()) == []

            opts = MergedOptions.using({"items": MergedOptions()})
            assert list(opts["items"].items()) == []

describe "Converters":
    it "has a KeyValuePairs converter on MergedOptions":
        result = MergedOptions.KeyValuePairs([(["one"], "two"), (["three", "four"], "five")])
        assert dict(result.items()) == {"one": "two", "three": result.prefixed("three")}
        assert dict(result["three"].items()) == {"four": "five"}

    it "has a Attributes converter on MergedOptions":
        obj = type("obj", (object,), {"one": "two", "two": "three", "four": "five"})
        result = MergedOptions.Attributes(obj, ("one", "four"), lift="global")
        assert list(result.keys()) == ["global"]
        assert dict(result["global"].items()) == {"one": "two", "four": "five"}

    describe "Property Converter":
        it "takes a converter":
            converter = mock.Mock(name="converter")
            prop = ConverterProperty(converter)
            assert prop.converter is converter

        it "has a __get__ for instantiating the converter and calling convert":
            a = mock.Mock(name="a")
            b = mock.Mock(name="b")
            c = mock.Mock(name="c")
            d = mock.Mock(name="d")
            converted = mock.Mock(name="converted")
            instance = mock.Mock(name="instance")

            converter = mock.Mock(name="converter")
            converter.return_value = instance
            instance.convert.return_value = converted

            prop = ConverterProperty(converter)
            assert prop.__get__()(c, d, a=b, b=a) is converted

            converter.assert_called_once_with(c, d, a=b, b=a)
            instance.convert.assert_called_once_with()

        it "can be used as a property":
            givenresult = mock.Mock(name="givenresult")
            producedresult = mock.Mock(name="producedresult")

            class Converter(object):
                def __init__(self, given):
                    self.given = given

                def convert(self):
                    return (self.given, producedresult)

            class Thing(object):
                myprop = ConverterProperty(Converter)

            assert Thing().myprop(givenresult) == (givenresult, producedresult)

    describe "KeyValuePairsConverter":
        it "converts simple key value pairs into a dictionary":
            converter = KeyValuePairsConverter([(["one"], "two"), (["3"], 4)])
            assert dict(converter.convert().items()) == {"one": "two", "3": 4}

        it "converts complex key value pairs into a dictionary":
            converted = KeyValuePairsConverter(
                [
                    (["one", "two"], "three"),
                    (["three"], "four"),
                    (["five", "six", "seven"], "eight"),
                    (["five", "six", "nine"], "ten"),
                ]
            ).convert()
            assert dict(converted.items()) == {
                "one": converted.prefixed("one"),
                "three": "four",
                "five": converted.prefixed("five"),
            }
            assert dict(converted["five"].items()) == {"six": converted["five"].prefixed("six")}
            six = converted["five"]["six"]
            assert dict(converted["five"]["six"].items()) == {"seven": "eight", "nine": "ten"}
            assert dict(converted["one"].items()) == {"two": "three"}

        it "Overrides previous keys":
            converted = KeyValuePairsConverter(
                [(["one", "two"], "three"), (["one", "two", "five"], "four")]
            ).convert()
            assert dict(converted.items()) == {"one": converted.prefixed("one")}
            assert dict(converted["one"].items()) == {"two": converted["one"].prefixed("two")}
            assert dict(converted["one"]["two"].items()) == {"five": "four"}

            # And the other way round
            converted = KeyValuePairsConverter(
                [(["one", "two", "five"], "four"), (["one", "two"], "three")]
            ).convert()
            assert dict(converted.items()) == {"one": converted.prefixed("one")}
            assert dict(converted["one"].items()) == {"two": "three"}

    describe "AttributesConverter":
        it "converts all attributes to a dictionary":

            class Obj(object):
                def a(self):
                    pass

                one = "two"

            class Obj2(Obj):
                def b(self):
                    pass

                three = "four"
                _ignored = "because_private"

            obj = Obj2()
            converted = AttributesConverter(obj).convert()
            assert dict(converted.items()) == {
                "one": "two",
                "three": "four",
                "b": obj.b,
                "a": obj.a,
            }

        it "includes underscored attributes if asked for":

            class Obj(object):
                def a(self):
                    pass

                one = "two"

            class Obj2(Obj):
                def b(self):
                    pass

                three = "four"
                _notignored = "because_private"

            obj = Obj2()
            converted = AttributesConverter(obj, include_underlined=True).convert()
            underlined = [attr for attr in dir(obj) if attr.startswith("_")]

            expected = dict((attr, getattr(obj, attr)) for attr in underlined)
            expected.update(
                {
                    "one": "two",
                    "three": "four",
                    "b": obj.b,
                    "a": obj.a,
                    "_notignored": "because_private",
                }
            )
            expected["__dict__"] = converted.prefixed("__dict__")
            assert dict(converted.items()) == expected

        it "only includes specified attributes if specified":

            class Obj(object):
                def a(self):
                    pass

                one = None
                blah = "things"
                hi = "hello"

            converter = AttributesConverter(Obj(), ("one", "hi", "__class__"))
            assert dict(converter.convert().items()) == {
                "one": None,
                "hi": "hello",
                "__class__": Obj,
            }

        it "can exclude attributes that have particular values":

            class Obj(object):
                def a(self):
                    pass

                one = None
                blah = "things"
                hi = "hello"

            converter = AttributesConverter(
                Obj(), ("one", "hi", "__class__"), ignoreable_values=(None,)
            )
            assert dict(converter.convert().items()) == {"hi": "hello", "__class__": Obj}

        it "can lift the result if provided with a prefix to lift against":

            class Obj(object):
                def a(self):
                    pass

                one = "two"
                blah = "things"
                hi = "hello"

            converted = AttributesConverter(
                Obj(), ("one", "hi", "__class__"), lift=["cats", "pandas"]
            ).convert()
            assert dict(converted.items()) == {"cats": converted.prefixed("cats")}
            assert list(converted["cats"].keys()) == ["pandas"]
            assert dict(converted["cats"]["pandas"].items()) == {
                "one": "two",
                "hi": "hello",
                "__class__": Obj,
            }
