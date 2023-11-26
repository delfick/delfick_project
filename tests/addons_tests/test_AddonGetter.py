# coding: spec

import uuid
from unittest import mock

import pytest

from delfick_project.addons import AddonGetter, addon_hook
from delfick_project.errors_pytest import assertRaises
from delfick_project.norms import Meta

describe "AddonGetter":
    it "defaults a delfick_project.addons namespace":
        assert list(AddonGetter().namespaces.keys()) == ["delfick_project.addons"]

    describe "add_namespace":
        it "registers result_spec and addon_spec in the namespaces dict":
            result_spec = mock.Mock(name="result_spec")
            addon_spec = mock.Mock(name="addon_spec")
            namespace = mock.Mock(name="namespace")

            getter = AddonGetter()
            getter.add_namespace(namespace, result_spec, addon_spec)

        it "finds entry points for that namespace":
            ep1 = mock.Mock(name="ep1")
            ep1.name = "entry1"
            ep2 = mock.Mock(name="ep2")
            ep2.name = "entry2"
            ep3 = mock.Mock(name="ep3")
            ep3.name = "entry2"
            namespace = mock.Mock(name="namespace")

            def iter_entry_points(ns):
                return {"delfick_project.addons": [], namespace: [ep1, ep2, ep3]}[ns]

            fake_iter_entry_points = mock.Mock(
                name="iter_entry_points", side_effect=iter_entry_points
            )

            with mock.patch(
                "delfick_project.addons.pkg_resources.iter_entry_points", fake_iter_entry_points
            ):
                getter = AddonGetter()
                assert getter.entry_points == {"delfick_project.addons": {}}
                getter.add_namespace(namespace)
                assert getter.entry_points == {
                    "delfick_project.addons": {},
                    namespace: {"entry1": [ep1], "entry2": [ep2, ep3]},
                }

            assert fake_iter_entry_points.mock_calls == [
                mock.call("delfick_project.addons"),
                mock.call(namespace),
            ]

    describe "all_for":
        it "yields nothing if we don't know about the namespace":
            assert list(AddonGetter().all_for("blah")) == []

        it "yields all known names for namespace":
            getter = AddonGetter()
            getter.entry_points["blah"] = {
                "one": mock.Mock(name="one"),
                "two": mock.Mock(name="two"),
            }
            assert sorted(getter.all_for("blah")) == sorted([("blah", "one"), ("blah", "two")])

    describe "get":

        @pytest.fixture()
        def getter(self):
            return AddonGetter()

        @pytest.fixture()
        def collector(self):
            return mock.Mock(name="collector")

        it "Logs a warning and does nothing if namespace is unknown", getter, collector:
            assert "bob" not in getter.namespaces
            assert getter("bob", "one", collector) is None

        it "finds all the entry points and resolved the into the addon_spec", getter:
            meta = Meta.empty()
            known = mock.Mock(name="known")
            result = mock.Mock(name="result")
            normalised = mock.Mock(name="normalised")

            result_spec = mock.Mock(name="result_spec", spec=["normalise"])
            addon_spec = mock.Mock(name="addons_spec", spec=["normalise"])

            namespace = mock.Mock(name="namespace")
            collector = mock.Mock(name="collector")
            entry_point_name = mock.Mock(name="entry_point_name")
            addon_spec.normalise.return_value = normalised
            result_spec.normalise.return_value = result

            ep1 = mock.Mock(name="ep1")
            entry_points = [ep1]
            fake_find_entry_points = mock.Mock(name="find_entry_points", return_value=entry_points)

            extras = mock.Mock(name="extra")
            resolver = mock.Mock(name="resolver")
            fake_resolve_entry_points = mock.Mock(
                name="resolve_entry_points", return_value=(resolver, extras)
            )

            getter.add_namespace(namespace, result_spec, addon_spec)

            with mock.patch.multiple(
                getter,
                find_entry_points=fake_find_entry_points,
                resolve_entry_points=fake_resolve_entry_points,
            ):
                assert getter(namespace, entry_point_name, collector, known) == normalised

            addon_spec.normalise.assert_called_once_with(
                meta,
                {
                    "namespace": namespace,
                    "name": entry_point_name,
                    "resolver": resolver,
                    "extras": extras,
                },
            )

            entry_point_full_name = "{0}.{1}".format(namespace, entry_point_name)
            fake_find_entry_points.assert_called_once_with(
                namespace, entry_point_name, entry_point_full_name
            )
            fake_resolve_entry_points.assert_called_once_with(
                namespace,
                entry_point_name,
                collector,
                mock.ANY,
                entry_points,
                entry_point_full_name,
                known,
            )

            addon_spec.normalise.assert_called_once_with(
                meta,
                {
                    "namespace": namespace,
                    "name": entry_point_name,
                    "resolver": resolver,
                    "extras": extras,
                },
            )

            result_maker = fake_resolve_entry_points.mock_calls[0][1][3]
            assert result_maker(blah="one") is result
            meta = Meta({"blah": "one"}, [])
            result_spec.normalise.assert_called_once_with(meta, {"blah": "one"})

    describe "find_entry_points":

        @pytest.fixture()
        def ms(self):
            class Mocks:
                namespace = mock.Mock(name="namesapce")
                entry_point_name = mock.Mock(name="entry_point_name")

            Mocks.entry_point_full_name = "{0}.{1}".format(Mocks.namespace, Mocks.entry_point_name)
            return Mocks

        it "uses pkg_resources.iter_entry_points", ms:
            ep = mock.Mock(name="ep")
            ep.name = ms.entry_point_name
            fake_iter_entry_points = mock.Mock(name="iter_entry_points", return_value=[ep])

            with mock.patch(
                "delfick_project.addons.pkg_resources.iter_entry_points", fake_iter_entry_points
            ):
                res = AddonGetter()
                res.add_namespace(ms.namespace)
                found = res.find_entry_points(
                    ms.namespace, ms.entry_point_name, ms.entry_point_full_name
                )
                assert found == [ep]

        it "complains if it finds no entry points", ms:
            fake_iter_entry_points = mock.Mock(name="iter_entry_points", return_value=[])

            with assertRaises(AddonGetter.NoSuchAddon, addon=ms.entry_point_full_name):
                with mock.patch(
                    "delfick_project.addons.pkg_resources.iter_entry_points", fake_iter_entry_points
                ):
                    res = AddonGetter()
                    res.add_namespace(ms.namespace)
                    res.find_entry_points(
                        ms.namespace, ms.entry_point_name, ms.entry_point_full_name
                    )

        it "uses all found entry points if it finds many", ms:
            ep = mock.Mock(name="ep")
            ep.name = ms.entry_point_name
            ep2 = mock.Mock(name="ep2")
            ep2.name = ms.entry_point_name
            fake_iter_entry_points = mock.Mock(name="iter_entry_points", return_value=[ep, ep2])

            with mock.patch(
                "delfick_project.addons.pkg_resources.iter_entry_points", fake_iter_entry_points
            ):
                res = AddonGetter()
                res.add_namespace(ms.namespace)
                found = res.find_entry_points(
                    ms.namespace, ms.entry_point_name, ms.entry_point_full_name
                )
                assert found == [ep, ep2]

    describe "resolve_entry_points":

        @pytest.fixture()
        def ms(self):
            class Mocks:
                namespace = mock.Mock(name="namespace")
                entry_point_name = mock.Mock(name="entry_point_name")
                collector = mock.Mock(name="collector")
                result_maker = mock.Mock(name="result_maker")

                module_name1 = str(uuid.uuid1())
                module_name2 = str(uuid.uuid1())

            return Mocks

        @pytest.fixture()
        def entry(self, ms):
            class Entry:
                ep1 = mock.Mock(name="ep1", module_name=ms.module_name1)
                ep2 = mock.Mock(name="ep2", module_name=ms.module_name2)

            Entry.entry_points = [Entry.ep1, Entry.ep2]
            Entry.entry_point_full_name = mock.Mock(name="entry_point_full_name")
            return Entry

        @pytest.fixture()
        def getter(self):
            return AddonGetter()

        it "passes on the error if it can't resolve any of the entry points", getter, entry, ms:
            e1 = ImportError("nup")
            entry.ep1.resolve.side_effect = e1
            entry.ep1.resolve.return_value = {}

            with assertRaises(ImportError, "nup"):
                getter.resolve_entry_points(
                    ms.namespace,
                    ms.entry_point_name,
                    ms.collector,
                    ms.result_maker,
                    entry.entry_points,
                    entry.entry_point_full_name,
                    [],
                )

        it "gets a resolver and returns it with the extras", getter, entry, ms:
            entry.ep1.resolve.return_value = type(
                "module",
                (object,),
                {"hook": addon_hook(extras=[("one", "two")])(lambda *args, **kwargs: None)},
            )
            entry.ep2.resolve.return_value = type("module", (object,), {})

            resolver = mock.Mock(name="resolver")
            fake_get_resolver = mock.Mock(name="get_resolver", return_value=resolver)

            hooks, extras = getter.resolve_entry_points(
                ms.namespace,
                ms.entry_point_name,
                ms.collector,
                ms.result_maker,
                entry.entry_points,
                entry.entry_point_full_name,
                [],
            )
            with mock.patch.object(getter, "get_resolver", fake_get_resolver):
                res = getter.resolve_entry_points(
                    ms.namespace,
                    ms.entry_point_name,
                    ms.collector,
                    ms.result_maker,
                    entry.entry_points,
                    entry.entry_point_full_name,
                    [],
                )
                assert res == (resolver, extras)

    describe "get_hooks_and_extras":
        it "finds hooks from the modules":
            hook1 = lambda *args, **kwargs: None
            module1 = type("module", (object,), {})
            module2 = type("module", (object,), {"hook": addon_hook()(hook1)})
            modules = [module1, module2]

            assert AddonGetter().get_hooks_and_extras(modules, []) == ([module2.hook], [])

        it "can find multiple hooks from the modules":
            hook1 = lambda *args, **kwargs: None
            hook2 = lambda *args, **kwargs: None
            module1 = type("module", (object,), {})
            module2 = type(
                "module",
                (object,),
                {
                    "hook": addon_hook()(hook1),
                    "other": addon_hook()(hook2),
                    "not_a_hook": lambda: None,
                },
            )
            modules = [module1, module2]

            assert AddonGetter().get_hooks_and_extras(modules, []) == (
                [module2.hook, module2.other],
                [],
            )

        it "can find multiple hooks from multiple modules":
            hook1 = lambda *args, **kwargs: None
            hook2 = lambda *args, **kwargs: None
            hook3 = lambda *args, **kwargs: None
            module1 = type("module", (object,), {"fasf": addon_hook()(hook3)})
            module2 = type(
                "module",
                (object,),
                {
                    "hook": addon_hook()(hook1),
                    "other": addon_hook()(hook2),
                    "not_a_hook": lambda: None,
                },
            )
            modules = [module1, module2]

            assert AddonGetter().get_hooks_and_extras(modules, []) == (
                [module1.fasf, module2.hook, module2.other],
                [],
            )

        it "finds extras from the hooks":
            hook1 = lambda *args, **kwargs: None
            hook2 = lambda *args, **kwargs: None
            hook3 = lambda *args, **kwargs: None
            module1 = type(
                "module", (object,), {"fasf": addon_hook(extras=[("one", "two")])(hook3)}
            )
            module2 = type(
                "module",
                (object,),
                {
                    "hook": addon_hook(extras=[("one", "three")])(hook1),
                    "other": addon_hook(extras=[("four", "five")])(hook2),
                    "not_a_hook": lambda: None,
                },
            )
            modules = [module1, module2]

            assert AddonGetter().get_hooks_and_extras(modules, []) == (
                [module1.fasf, module2.hook, module2.other],
                [("one", "two"), ("one", "three"), ("four", "five")],
            )

        it "deals with __all__":
            hook1 = lambda *args, **kwargs: None
            module1 = type(
                "module",
                (object,),
                {"asdf": addon_hook(extras=[("one", "one"), ("one", "__all__")])(hook1)},
            )
            modules = [module1]

            all_pairs = [("one", "one"), ("one", "two"), ("one", "three"), ("one", "four")]
            all_for = mock.Mock(name="all_for", return_value=all_pairs)

            with mock.patch.object(AddonGetter, "all_for", all_for):
                assert AddonGetter().get_hooks_and_extras(modules, [("one", "two")]) == (
                    [module1.asdf],
                    [("one", "one"), ("one", "four"), ("one", "three")],
                )

            all_for.assert_called_once_with("one")

    describe "get_resolver":

        @pytest.fixture()
        def ms(self):
            class Mocks:
                hooks = mock.Mock(name="hooks")
                collector = mock.Mock(name="collector")
                result_maker = mock.Mock(name="result_maker")

            return Mocks

        it "returns a function", ms:
            assert callable(AddonGetter().get_resolver(ms.collector, ms.result_maker, ms.hooks))

        it "calls just the post_register hooks if post_register is True and also gives them the kwargs", ms:
            called = []
            kw3 = mock.Mock(name="kw3")
            kw4 = mock.Mock(name="kw4")

            hook1 = addon_hook(post_register=True)(lambda c, kw3, kw4: called.append((c, 1)))
            hook2 = addon_hook(post_register=False)(lambda: called.append(2))
            hook3 = addon_hook(post_register=True)(lambda c, kw3, kw4: called.append((c, 3)))
            hook4 = addon_hook(post_register=False)(lambda: called.append(4))
            hooks = [hook1, hook2, hook3, hook4]

            resolver = AddonGetter().get_resolver(ms.collector, ms.result_maker, hooks)

            assert called == []
            list(resolver(post_register=True, kw3=kw3, kw4=kw4))
            assert called == [(ms.collector, 1), (ms.collector, 3)]

        it "calls non post_register hooks if post_register is False and passes in the collector and result_maker", ms:
            called = []

            hook1 = addon_hook(post_register=True)(lambda c, kw3, kw4: called.append((c, 1)))
            hook2 = addon_hook(post_register=False)(lambda c, r: called.append((c, r, 2)))
            hook3 = addon_hook(post_register=True)(lambda c, kw3, kw4: called.append((c, 3)))
            hook4 = addon_hook(post_register=False)(lambda c, r: called.append((c, r, 4)))
            hooks = [hook1, hook2, hook3, hook4]

            resolver = AddonGetter().get_resolver(ms.collector, ms.result_maker, hooks)

            assert called == []
            list(resolver(post_register=False))
            assert called == [
                (ms.collector, ms.result_maker, 2),
                (ms.collector, ms.result_maker, 4),
            ]
