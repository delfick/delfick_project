# coding: spec

from delfick_project.addons import Addon

from delfick_project.norms import Meta

from unittest import mock

describe "Addon":
    it "has name, a resolver and a namespace":
        resolver = mock.Mock(name="resolver")
        addon = Addon.FieldSpec().normalise(
            Meta.empty(), {"name": "bob", "resolver": resolver, "namespace": "stuff"}
        )
        assert addon.name == "bob"
        assert addon.resolver == resolver
        assert addon.namespace == "stuff"

    describe "resolved":
        it "Gets the list from calling the resolver":
            resolved = mock.Mock(name="resolved")
            resolver = mock.Mock(name="resolver", return_value=[resolved])
            addon = Addon(name="a1", resolver=resolver, namespace="yeap", extras=[])
            assert addon.resolved == [resolved]

            # And it gets memoized
            assert addon.resolved == [resolved]
            resolver.assert_called_once_with()
            resolver.assert_called_once_with()

    describe "process":
        it "does nothing if the collector is None":
            specs1 = mock.Mock(name="specs1")
            rs1 = mock.Mock(name="rs1")
            rs1.get.return_value = [specs1]
            resolver = mock.Mock(name="resolver", return_value=[rs1])

            addon = Addon(name="a2", resolver=resolver, namespace="stuff", extras=[])
            addon.process(None)

            assert True, "this should not have failed"

        it "registers converters for all the resolved":
            specs1 = mock.Mock(name="specs1")
            specs2 = mock.Mock(name="specs2")
            specs3 = mock.Mock(name="specs3")

            rs1 = mock.Mock(name="rs1")
            rs2 = mock.Mock(name="rs2")
            rs3 = mock.Mock(name="rs3")

            rs1.get.return_value = [specs1, specs2]
            rs2.get.return_value = [specs3]
            rs3.get.return_value = None

            resolver = mock.Mock(name="resolver", return_value=[rs1, rs2, rs3])

            configuration = mock.Mock(name="configuration")
            collector = mock.Mock(name="collector", configuration=configuration)

            addon = Addon(name="a2", resolver=resolver, namespace="stuff", extras=[])
            addon.process(collector)

            assert collector.register_converters.mock_calls == [
                mock.call([specs1, specs2]),
                mock.call([specs3]),
                mock.call(None),
            ]

    describe "post_register":
        it "calls the resolver with post_register=True and other kwargs":
            kw1 = mock.Mock(name="kw1")
            kw2 = mock.Mock(name="kw2")
            resolver = mock.Mock(name="resolver", return_value=[])

            addon = Addon(name="a3", resolver=resolver, namespace="things", extras=[])
            addon.post_register(kw1=kw1, kw2=kw2)

            resolver.assert_called_once_with(post_register=True, kw1=kw1, kw2=kw2)

    describe "unresolved_dependencies":
        it "returns extras from the addon instead of it's results":
            resolver = mock.NonCallableMock(name="resolver")
            addon = Addon(name="a3", resolver=resolver, namespace="thing", extras=[("one", "two")])
            assert list(addon.unresolved_dependencies()) == [("one", "two")]

    describe "resolved_dependencies":
        it "returns extras from the resolved results":
            rs1 = mock.Mock(name="rs1")
            rs2 = mock.Mock(name="rs2")

            rs1.get.return_value = [("three", "five")]
            rs2.get.return_value = [("three", "four")]

            resolver = mock.Mock(name="resolver", return_value=[rs1, rs2])

            addon = Addon(name="a3", resolver=resolver, namespace="thing", extras=[("one", "two")])
            assert list(addon.resolved_dependencies()) == [("three", "five"), ("three", "four")]

            rs1.get.assert_called_once_with("extras", [])
            rs2.get.assert_called_once_with("extras", [])

    describe "dependencies":
        it "only returns unresolved_dependencies if haven't resolved yet":
            rs1 = mock.Mock(name="rs1")
            rs2 = mock.Mock(name="rs2")

            rs1.get.return_value = [("three", "five")]
            rs2.get.return_value = [("three", "four")]

            resolver = mock.Mock(name="resolver", return_value=[rs1, rs2])

            addon = Addon(name="a3", resolver=resolver, namespace="thing", extras=[("one", "two")])
            assert list(addon.dependencies(mock.Mock(name="all_deps"))) == [("one", "two")]

        it "returns all deps if we've previously resolved":
            rs1 = mock.Mock(name="rs1")
            rs2 = mock.Mock(name="rs2")

            rs1.get.return_value = [("three", "five")]
            rs2.get.return_value = [("three", "four")]

            resolver = mock.Mock(name="resolver", return_value=[rs1, rs2])

            addon = Addon(name="a3", resolver=resolver, namespace="thing", extras=[("one", "two")])
            assert addon.resolved == [rs1, rs2]
            assert list(addon.dependencies(mock.Mock(name="all_deps"))) == [
                ("one", "two"),
                ("three", "five"),
                ("three", "four"),
            ]
