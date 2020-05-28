# coding: spec

from delfick_project.option_merge.storage import Storage, DataPath
from delfick_project.option_merge import MergedOptions, NotFound
from delfick_project.option_merge.path import Path
from delfick_project.norms import dictobj

from delfick_project.errors_pytest import assertRaises

from unittest import mock
import pytest


d1 = mock.Mock(name="d1", spec=[])
d2 = mock.Mock(name="d2", spec=[])
d3 = mock.Mock(name="d3", spec=[])
d4 = mock.Mock(name="d4", spec=[])
d5 = mock.Mock(name="d5", spec=[])
d6 = mock.Mock(name="d6", spec=[])
d7 = mock.Mock(name="d7", spec=[])
d8 = mock.Mock(name="d8", spec=[])

p1 = mock.Mock(name="p1")
p2 = mock.Mock(name="p2")
p3 = mock.Mock(name="p3")
p4 = mock.Mock(name="p4")
p5 = mock.Mock(name="p5")
p6 = mock.Mock(name="p6")

s1 = mock.Mock(name="s1")
s2 = mock.Mock(name="s2")
s3 = mock.Mock(name="s3")
s4 = mock.Mock(name="s4")
s5 = mock.Mock(name="s5")
s6 = mock.Mock(name="s6")

c1 = mock.Mock(name="c1")
c2 = mock.Mock(name="c2")
c3 = mock.Mock(name="c3")
c4 = mock.Mock(name="c4")
c5 = mock.Mock(name="c5")
c6 = mock.Mock(name="c6")


@pytest.fixture()
def storage():
    return Storage()


describe "Storage":
    it "Has data and deleted paths", storage:
        assert storage.deleted == []
        assert storage.data == []

    it "adds new data at the start", storage:
        path1 = Path(mock.Mock(name="path1"))
        path2 = Path(mock.Mock(name="path2"))

        data1 = mock.Mock(name="data1")
        data2 = mock.Mock(name="data2")

        source1 = mock.Mock(name="source1")
        source2 = mock.Mock(name="source2")

        assert storage.deleted == []
        assert storage.data == []

        storage.add(path1, data1, source=source1)
        assert storage.deleted == []
        assert storage.data == [(path1, data1, source1)]

        storage.add(path2, data2, source=source2)
        assert storage.deleted == []
        assert storage.data == [(path2, data2, source2), (path1, data1, source1)]

    describe "Deleting":
        it "removes first thing with the same path", storage:
            storage.add(Path(["a", "b"]), d1)
            storage.add(Path(["b", "c"]), d2)
            storage.add(Path(["a", "b"]), d3)
            assert storage.data == [
                (["a", "b"], d3, None),
                (["b", "c"], d2, None),
                (["a", "b"], d1, None),
            ]
            storage.delete("a.b")
            assert storage.data == [(["b", "c"], d2, None), (["a", "b"], d1, None)]

        it "removes first thing starting with the same path", storage:
            storage.add(Path(["a", "b", "c"]), d1)
            storage.add(Path(["b", "c"]), d2)
            storage.add(Path(["a", "b", "d"]), d3)
            storage.add(Path(["a", "bd"]), d4)
            assert storage.data == [
                (["a", "bd"], d4, None),
                (["a", "b", "d"], d3, None),
                (["b", "c"], d2, None),
                (["a", "b", "c"], d1, None),
            ]
            storage.delete("a.b")
            assert storage.data == [
                (["a", "bd"], d4, None),
                (["b", "c"], d2, None),
                (["a", "b", "c"], d1, None),
            ]

            storage.delete("a.b")
            assert storage.data == [(["a", "bd"], d4, None), (["b", "c"], d2, None)]

        it "deletes inside the info if it can", storage:
            storage.add(Path(["a", "b", "c"]), d1)
            storage.add(Path(["b", "c"]), d2)
            storage.add(Path(["a", "b"]), d3)
            storage.add(Path(["a", "bd"]), d4)

            def delete_from_data_func(d, p):
                if d is d1:
                    return True
                elif d is d3:
                    return False
                else:
                    assert False, "Unexpected inputs to delete_from_data: d={0}\tp={1}".format(d, p)

            delete_from_data = mock.Mock(name="delete_from_data")
            delete_from_data.side_effect = delete_from_data_func

            with mock.patch.object(storage, "delete_from_data", delete_from_data):
                storage.delete("a.b.c.d")

            assert delete_from_data.mock_calls == [mock.call(d3, "c.d"), mock.call(d1, "d")]

        it "raises an Index error if it can't find the key", storage:
            storage.add(Path(["a", "b", "c"]), d1)
            storage.add(Path(["b", "c"]), d2)
            storage.add(Path(["a", "b", "d"]), d3)
            storage.add(Path(["a", "bd"]), d4)
            assert storage.data == [
                (["a", "bd"], d4, None),
                (["a", "b", "d"], d3, None),
                (["b", "c"], d2, None),
                (["a", "b", "c"], d1, None),
            ]

            with assertRaises(KeyError, "a.c"):
                storage.delete("a.c")

        it "works with empty path", storage:
            storage.add(Path([]), {"a": "b"})
            storage.add(Path([]), {"c": "d"})
            storage.add(Path([]), {"a": {"d": "e"}})
            assert storage.data == [
                ([], {"a": {"d": "e"}}, None),
                ([], {"c": "d"}, None),
                ([], {"a": "b"}, None),
            ]

            storage.delete("a.d")
            assert storage.data == [
                ([], {"a": {}}, None),
                ([], {"c": "d"}, None),
                ([], {"a": "b"}, None),
            ]

            storage.delete("a")
            assert storage.data == [([], {}, None), ([], {"c": "d"}, None), ([], {"a": "b"}, None)]

            storage.delete("a")
            assert storage.data == [([], {}, None), ([], {"c": "d"}, None), ([], {}, None)]

    describe "Delete from data":
        it "returns False if the data is not a dictionary", storage:
            for data in (0, 1, True, False, None, [], [1], mock.Mock(name="object"), lambda: 1):
                assert not storage.delete_from_data(data, "one.blah")

        it "returns False if the data is a dictionary without desired key", storage:
            for data in ({}, {1: 2}, {"two": 2}):
                assert not storage.delete_from_data(data, "one.blah")

        it "deletes the item and returns True if the data contains the key", storage:
            data = {"one": 1, "two": 2, "three.four": 3}
            res = storage.delete_from_data(data, "one")
            assert data == {"two": 2, "three.four": 3}
            assert res is True

            res = storage.delete_from_data(data, "three.four")
            assert data == {"two": 2}
            assert res is True

        it "says false if given an empty string to delete", storage:
            data = {"one": 1, "two": 2, "three.four": 3}
            res = storage.delete_from_data(data, "")
            assert data == {"one": 1, "two": 2, "three.four": 3}
            assert res is False

        it "deletes full keys before sub keys", storage:
            data = {"one": 1, "two": 2, "three.four": 3, "three": {"four": 5}}
            res = storage.delete_from_data(data, "three.four")
            assert data == {"one": 1, "two": 2, "three": {"four": 5}}
            assert res is True

        it "deletes into dictionaries", storage:
            data = {"one": {"two": {"three.four": {"five": 6}, "seven": 7}}}
            res = storage.delete_from_data(data, "one.two.three.four.five")
            assert data == {"one": {"two": {"three.four": {}, "seven": 7}}}
            assert res is True

    describe "Getting path and val":
        describe "Same path as info_path":
            it "returns data as is with info_path as the full_path", storage:
                path = Path("a.bd.1")
                info_path = ["a", "bd", "1"]
                data = mock.Mock(name="data")
                source = mock.Mock(name="source")

                assert (list(storage.determine_path_and_val(path, info_path, data, source))) == [
                    (info_path, "", data)
                ]

        describe "No info_path":
            it "returns value into data", storage:
                val = mock.Mock(name="val")
                data = {"a": {"b": val}}
                path = Path(["a", "b"])
                info_path = []
                source = mock.Mock(name="source")

                assert (list(storage.determine_path_and_val(path, info_path, data, source))) == [
                    (["a", Path("b")], "a.b", val)
                ]

            it "yields nothing if path not in data", storage:
                val = mock.Mock(name="val")
                data = {"e": {"b": val}}
                path = Path(["a", "b"])
                info_path = []
                source = mock.Mock(name="source")

                assert (list(storage.determine_path_and_val(path, info_path, data, source))) == []

        describe "Path begins with info_path":
            it "returns found val or dict in the data from path remainder after info_path", storage:
                val = mock.Mock(name="val")
                data = {"b": {"c": {"d": val}}, "e": 1, "f": 2}
                info_path = Path("a")
                path = Path("a.b")
                source = mock.Mock(name="source")

                assert (list(storage.determine_path_and_val(path, info_path, data, source))) == [
                    (["a", "b"], "b", {"c": {"d": val}})
                ]

            it "yields nothing if rest of path not in data", storage:
                val = mock.Mock(name="val")
                data = {"e": {"c": {"d": val}}, "f": 1, "g": 2}
                info_path = Path("a")
                path = Path("a.b")
                source = mock.Mock(name="source")

                assert (list(storage.determine_path_and_val(path, info_path, data, source))) == []

        describe "Info_path begins with path":
            it "returns made dictionary with remainder info_path", storage:
                data = mock.Mock(name="data")
                info_path = ["a", "b.e", "c", "d"]
                path = Path("a.b.e")
                source = mock.Mock(name="source")

                assert (list(storage.determine_path_and_val(path, info_path, data, source))) == [
                    (["a", "b.e"], "", {"c": {"d": data}})
                ]

    describe "Getting info":
        it "returns all the values it finds", storage:
            storage.add(Path(["a", "b", "c"]), d1, source=s1)
            storage.add(Path(["b", "c"]), d2, source=s5)
            storage.add(Path(["a", "b", "d"]), d3, source=s4)
            storage.add(Path(["a", "bd"]), {"1": d4}, source=s2)
            storage.add(Path([]), {"a": {"bd": d4}}, source=s1)
            storage.add(Path(["a", "b", "c", "d", "e"]), d5, source=s5)
            storage.add(Path(["a", "b", "c"]), {"d": {"e": d6}}, source=s6)

            assert storage.data == [
                (["a", "b", "c"], {"d": {"e": d6}}, s6),
                (["a", "b", "c", "d", "e"], d5, s5),
                ([], {"a": {"bd": d4}}, s1),
                (["a", "bd"], {"1": d4}, s2),
                (["a", "b", "d"], d3, s4),
                (["b", "c"], d2, s5),
                (["a", "b", "c"], d1, s1),
            ]

            path1 = Path("a.bd")
            path2 = Path("a.b.c")
            path3 = Path("a.bd.1")
            path4 = Path("")

            assert (list((p.path, p.data, p.source()) for p in storage.get_info(path1))) == [
                (Path("a.bd"), d4, s1),
                (Path("a.bd"), {"1": d4}, s2),
            ]
            assert (list((p.path, p.data, p.source()) for p in storage.get_info(path2))) == [
                (["a", "b", "c"], {"d": {"e": d6}}, s6),
                (["a", "b", "c"], {"d": {"e": d5}}, s5),
                (["a", "b", "c"], d1, s1),
            ]
            assert (list((p.path, p.data, p.source()) for p in storage.get_info(path3))) == [
                (["a", "bd", "1"], d4, s2)
            ]
            assert (list((p.path, p.data, p.source()) for p in storage.get_info(path4))) == [
                (Path(""), {"a": {"b": {"c": {"d": {"e": d6}}}}}, s6),
                (Path(""), {"a": {"b": {"c": {"d": {"e": d5}}}}}, s5),
                (Path(""), {"a": {"bd": d4}}, s1),
                (Path(""), {"a": {"bd": {"1": d4}}}, s2),
                (Path(""), {"a": {"b": {"d": d3}}}, s4),
                (Path(""), {"b": {"c": d2}}, s5),
                (Path(""), {"a": {"b": {"c": d1}}}, s1),
            ]

        it "returns DataPath objects if that's what it finds", storage:
            storage.add(Path(["a", "b", "c"]), d1, source=s1)
            storage.add(Path(["b", "c"]), d2, source=s2)
            storage.add(Path(["a", "b", "d"]), d3, source=s3)
            storage.add(Path(["a", "bd"]), {"1": d4}, source=s4)
            assert storage.data == [
                (["a", "bd"], {"1": d4}, s4),
                (["a", "b", "d"], d3, s3),
                (["b", "c"], d2, s2),
                (["a", "b", "c"], d1, s1),
            ]

            assert list((p.path, p.data, p.source()) for p in storage.get_info("a")) == [
                (Path(["a"]), {"bd": {"1": d4}}, s4),
                (Path(["a"]), {"b": {"d": d3}}, s3),
                (Path(["a"]), {"b": {"c": d1}}, s1),
            ]

        it "raises KeyError if no key is found", storage:
            storage.add(Path(["a", "b", "c"]), d1)
            storage.add(Path(["b", "c"]), d2)
            storage.add(Path(["a", "b", "d"]), d3)
            storage.add(Path(["a", "bd"]), {"1": d4})
            assert storage.data == [
                (["a", "bd"], {"1": d4}, None),
                (["a", "b", "d"], d3, None),
                (["b", "c"], d2, None),
                (["a", "b", "c"], d1, None),
            ]

            with assertRaises(KeyError, "e.g"):
                list(storage.get_info("e.g"))

    describe "get":
        it "returns data from the first info", storage:
            data = mock.Mock(name="data")
            path = Path(mock.Mock(name="path"))

            info = mock.Mock(name="info", spec=["data"])
            info2 = mock.Mock(name="info2", spec=["data"])
            info.data = data

            get_info = mock.Mock(name="get_info")
            get_info.return_value = [info, info2]

            with mock.patch.object(storage, "get_info", get_info):
                assert storage.get(path) is data

            get_info.assert_called_once_with(path)

        it "raises KeyError if no info for that key", storage:
            path = Path
            (mock.Mock(name="path"))
            get_info = mock.Mock(name="get_info")
            get_info.return_value = []

            with assertRaises(KeyError, str(path)):
                with mock.patch.object(storage, "get_info", get_info):
                    storage.get(path)

            get_info.assert_called_once_with(path)

    describe "Getting source":
        it "returns all sources that contain the provided path", storage:
            storage.add(Path(["a", "b", "c"]), d1, source=s1)
            storage.add(Path(["b", "c"]), d2, source=s5)
            storage.add(Path(["a", "b", "d"]), d3, source=s4)
            storage.add(Path(["a", "bd"]), {"1": d4}, source=s2)
            storage.add(Path([]), {"a": {"bd": d4}}, source=s1)
            storage.add(Path(["a", "b", "c", "d", "e"]), d5, source=s5)
            storage.add(Path(["a", "b", "c"]), {"d": {"e": d6}}, source=s6)
            assert storage.data == [
                (["a", "b", "c"], {"d": {"e": d6}}, s6),
                (["a", "b", "c", "d", "e"], d5, s5),
                ([], {"a": {"bd": d4}}, s1),
                (["a", "bd"], {"1": d4}, s2),
                (["a", "b", "d"], d3, s4),
                (["b", "c"], d2, s5),
                (["a", "b", "c"], d1, s1),
            ]

            assert storage.source_for(Path("a.b.c")) == [s6, s5, s1]
            assert storage.source_for(Path("a.b.c.d.e")) == [s6, s5]
            assert storage.source_for(Path("a.b.c.d")) == [s6, s5]
            assert storage.source_for(Path("a.bd")) == [s1, s2]
            assert storage.source_for(Path("a.bd.1")) == [s2]

    describe "keys_after":
        it "yields combined keys from datas", storage:
            storage.add(Path([]), {"a": 1, "b": 2})
            storage.add(Path([]), {"b": 3, "d": 4})
            assert sorted(storage.keys_after("")) == sorted(["a", "b", "d"])

        it "yields from incomplete paths", storage:
            storage.add(Path(["1", "2", "3"]), {"a": 1, "b": 2})
            assert sorted(storage.keys_after("1")) == sorted(["2"])

        it "stops after complete paths", storage:
            storage.add(Path(["1", "2", "3"]), {"a": 1, "b": 2})
            storage.add(Path(["1"]), d1)
            assert sorted(storage.keys_after("1")) == sorted([])

    describe "as_dict":
        it "Returns the dictionary if there is only one", storage:
            storage.add(Path([]), {"a": 1, "b": 2})
            assert storage.as_dict(Path([])) == {"a": 1, "b": 2}

        it "merges from the back to the front if there is multiple dictionaries", storage:
            storage.add(Path([]), {"a": 1, "b": 2})
            storage.add(Path([]), {"a": 2, "c": 3})
            assert storage.as_dict(Path([])) == {"a": 2, "b": 2, "c": 3}

        it "returns the subpath that is provided", storage:
            storage.add(Path([]), {"a": {"d": 1}, "b": 2})
            storage.add(Path([]), {"a": {"d": 3}, "c": 3})
            assert storage.as_dict(Path(["a"])) == {"d": 3}

        it "returns subpath if the data is in storage with a prefix", storage:
            storage.add(Path([]), {"a": {"d": 1}, "b": 2})
            storage.add(Path(["a"]), {"d": 3})
            assert storage.as_dict(Path(["a"])) == {"d": 3}

        it "unrolls MergedOptions it finds", storage:
            options = MergedOptions.using({"f": 5})
            storage.add(Path([]), {"a": {"d": 1}, "b": 2})
            storage.add(Path(["a"]), {"d": 3, "e": options})
            assert storage.as_dict(Path(["a"])) == {"d": 3, "e": {"f": 5}}

        it "ignores unrelated dataz", storage:
            options = MergedOptions.using({"f": 5})
            storage.add(Path([]), {"g": {"d": 1}, "b": 2})
            storage.add(Path(["a"]), {"d": 3, "e": options})
            assert storage.as_dict(Path(["a"])) == {"d": 3, "e": {"f": 5}}

        it "doesn't infinitely recurse", storage:
            storage.add(Path([]), {"a": {"d": 1}, "b": MergedOptions(storage=storage)})
            storage.add(Path(["a"]), {"d": 3, "e": MergedOptions(storage=storage)})
            assert storage.as_dict(Path(["a"])) == {"d": 3, "e": {"a": {"e": {}, "d": 3}, "b": {}}}

        it "allows different parts of the same storage", storage:
            storage.add(Path([]), {"a": {"d": 1}, "b": 2})
            storage.add(Path(["a"]), {"d": 3, "e": MergedOptions(storage=storage)})
            assert storage.as_dict(Path(["a"])) == {"d": 3, "e": {"a": {"e": {}, "d": 3}, "b": 2}}

        it "works if the first item is a MergedOptions", storage:
            options = MergedOptions.using({"blah": {"stuff": 1}})
            options.update({"blah": {"stuff": 4, "meh": {"8": "9"}}})
            options["blah"].update({"stuff": {"tree": 20}})
            storage.add(Path([]), options)

            assert storage.as_dict(Path(["blah", "stuff"])) == {"tree": 20}
            assert storage.as_dict(Path(["blah", "meh"])) == {"8": "9"}

        it "works if the data is prefixed":
            options = MergedOptions()
            options[["blah", "stuff"]] = 1
            assert options.as_dict() == {"blah": {"stuff": 1}}

        it "works with dictobj objects and objects with their own as_dict":

            class Thing:
                def as_dict(s):
                    return {"a": 1}

            class D(dictobj):
                fields = ["thing"]

            m = MergedOptions.using(D(thing=Thing()), {"other": Thing()}, Thing(), {"b": 2})
            assert m.as_dict() == {"thing": {"a": 1}, "other": {"a": 1}, "a": 1, "b": 2}

describe "DataPath":
    it "takes in path, data and source":
        p1 = mock.Mock(name="p1")
        path = Path(p1)
        data = mock.Mock(name="data")
        source = mock.Mock(name="source")
        instance = DataPath(path, data, source)
        assert instance.path is path
        assert instance.data is data
        assert instance.source is source

    describe "keys_after":
        it "returns keys from data if path matches":
            p = DataPath(Path(["1", "2"]), {"a": 3, "b": 4}, s1)
            assert sorted(p.keys_after(Path("1.2"))) == sorted(["a", "b"])

            p = DataPath(Path(["1"]), {"a": 3, "b": 4}, s1)
            assert sorted(p.keys_after(Path("1"))) == sorted(["a", "b"])

            p = DataPath(Path([]), {"a": {1: 2}})
            assert sorted(p.keys_after(Path("a"))) == sorted([1])

        it "raises NotFound if no match":
            p = DataPath(Path(["1", "2"]), {"a": 3, "b": 4}, s1)
            with assertRaises(NotFound):
                assert sorted(p.keys_after(Path("1.3"))) == sorted([])

            with assertRaises(NotFound):
                assert sorted(p.keys_after(Path("3"))) == sorted([])

        it "returns first key after part if path is bigger":
            p = DataPath(Path(["1", "2", "3"]), {"a": 3, "b": 4}, s1)
            assert sorted(p.keys_after(Path("1"))) == sorted(["2"])

        it "raises NotFound if ask for a bigger path than exists":
            p = DataPath(Path(["1", "2", "3"]), {"a": 3, "b": 4}, s1)
            with assertRaises(NotFound):
                sorted(p.keys_after(Path("1.2.3.4")))

    describe "value_after":
        it "returns value":
            p = DataPath(Path(["a"]), d1, s1)
            assert p.value_after(Path("a")) is d1

            p = DataPath(Path([]), {"a": d1}, s1)
            assert p.value_after(Path("a")) is d1

        it "makes dicts from incomplete paths":
            p = DataPath(Path(["a", "b", "c"]), d1, s1)
            assert p.value_after(Path("a")) == {"b": {"c": d1}}

            p = DataPath(Path(["a", "b"]), {"c": d1}, s1)
            assert p.value_after(Path("a")) == {"b": {"c": d1}}

        it "raises NotFound if not found":
            p = DataPath(Path(["a", "b", "c"]), d1, s1)
            with assertRaises(NotFound):
                assert p.value_after(Path("b")) is None

            p = DataPath(Path(["a"]), {"b": d1}, s1)
            with assertRaises(NotFound):
                p.value_after(Path("a.c"))

            p = DataPath(Path(["1", "2", "3"]), {"a": 3, "b": 4}, s1)
            with assertRaises(NotFound):
                p.value_after(Path("1.2.3.4"))
