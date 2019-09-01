# coding: spec

from input_algorithms.meta import Meta

from noseOfYeti.tokeniser.support import noy_sup_setUp
from tests.helpers import TestCase
import mock

describe TestCase, "Meta":
    it "holds everything and a path":
        path = mock.Mock(name="path")
        everything = mock.Mock(name="everything")
        meta = Meta(everything, path)
        assert meta._path is path
        assert meta.everything is everything

    it "is equal to another meta with the same everything and path":
        assert Meta({}, [("hello", "")]) == Meta({}, []).at("hello")
        assert not Meta({}, [("hello", "[0]")]) == Meta({}, []).at("hello")

    it "is not equal to another meta with a different path":
        assert not Meta({}, [("hello", "")]) == Meta({}, []).at("there")

    it "can generate an empty Meta":
        assert Meta({}, []) == Meta.empty()

    describe "New path":
        before_each:
            self.p1 = mock.Mock(name="p1")
            self.p2 = mock.Mock(name="p2")
            self.path = [(self.p1, ""), (self.p2, "")]
            self.everything = mock.Mock(name="everything")
            self.meta = Meta(self.everything, self.path)

        describe "indexed_at":
            it "returns a new instance of itself with a new path saying indexed to some index":
                new_path = mock.Mock(name="new_path")
                with_new_path = mock.Mock(name="with_new_path")
                new_path.return_value = with_new_path

                with mock.patch.object(self.meta, "new_path", new_path):
                    assert self.meta.indexed_at(3) is with_new_path

                new_path.assert_called_once_with([("", "[3]")])

        describe "at":
            it "returns a new instance of itself with a new path saying it goes to some key":
                new_path = mock.Mock(name="new_path")
                with_new_path = mock.Mock(name="with_new_path")
                new_path.return_value = with_new_path

                with mock.patch.object(self.meta, "new_path", new_path):
                    assert self.meta.at("meh") is with_new_path

                new_path.assert_called_once_with([("meh", "")])

        describe "new_path":
            it "returns a new instance of the current class with an expanded path":
                p3 = mock.Mock(name="p3")

                class MetaSub(Meta):
                    pass

                meta = MetaSub(self.everything, self.path)
                assert meta._path == [(self.p1, ""), (self.p2, "")]

                new = meta.new_path([(p3, "")])
                assert meta._path == [(self.p1, ""), (self.p2, "")]
                assert new._path == [(self.p1, ""), (self.p2, ""), (p3, "")]
                assert new.everything is self.everything
                assert isinstance(new, MetaSub), type(new)

    describe "Joining the path":
        it "Joins each nonempty first item with dots and adds second items as extra":
            meta = Meta(
                mock.Mock(name="everything"),
                [("one", ""), ("two", "[3]"), ("", "[4]"), ("", ""), ("five", "")],
            )
            assert meta.path == "one.two[3][4].five"

    describe "Finding the source of something":
        it "returns unknown source_for":
            everything = mock.Mock(name="everything", spec=[])
            meta = Meta(everything, [("one", ""), ("two", "[3]")])
            assert meta.source == "<unknown>"

        it "asks everything for source if it has source_for":
            path = [(str(mock.Mock(name="path")), "")]
            source = mock.Mock(name="source")
            source_for = mock.Mock(name="source_for")
            everything = mock.Mock(name="everything")
            everything.source_for.return_value = source

            meta = Meta(everything, path)
            assert meta.source == source
            everything.source_for.assert_called_once_with(path[0][0])

        it "catches KeyError from finding the source":
            path = [(str(mock.Mock(name="path")), "")]
            everything = mock.Mock(name="everything")
            everything.source_for.side_effect = KeyError("path")

            meta = Meta(everything, path)
            assert meta.source == "<unknown>"
            everything.source_for.assert_called_once_with(path[0][0])

    describe "Formatting in a delfick error":
        it "formats with source and path":
            path = mock.Mock(name="path")
            everything = mock.Mock(name="everything")

            meta = Meta(everything, [("one", ""), ("three", ""), ("five", ""), ("", [1])])
            source = mock.Mock(name="source")
            everything.source_for.return_value = source

            assert meta.delfick_error_format(
                "blah"
            ) == "{{source={0}, path=one.three.five[1]}}".format(source)

        it "doesn't print out source if there is no source":
            path = mock.Mock(name="path")
            everything = mock.Mock(name="everything")

            meta = Meta(everything, [("one", ""), ("three", ""), ("five", ""), ("", [1])])

            everything.source_for.return_value = []
            assert meta.delfick_error_format("blah") == "{path=one.three.five[1]}"

            everything.source_for.return_value = None
            assert meta.delfick_error_format("blah") == "{path=one.three.five[1]}"

            everything.source_for.return_value = "<unknown>"
            assert meta.delfick_error_format("blah") == "{path=one.three.five[1]}"

    describe "Getting key names":
        it "returns all the parts of the path as _key_name_i":
            path = [("one", ""), ("two", "[]"), ("three", "")]
            meta = Meta(None, path)
            assert meta.key_names() == {
                "_key_name_0": "three",
                "_key_name_1": "two",
                "_key_name_2": "one",
            }
