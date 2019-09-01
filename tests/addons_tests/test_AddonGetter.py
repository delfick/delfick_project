# coding: spec

from option_merge_addons import AddonGetter, option_merge_addon_hook

from noseOfYeti.tokeniser.support import noy_sup_setUp
from input_algorithms.meta import Meta
from tests.helpers import TestCase
from operator import attrgetter
import mock

describe TestCase, "AddonGetter":
    it "defaults a option_merge.addons namespace":
        self.assertEqual(list(AddonGetter().namespaces.keys()), ["option_merge.addons"])

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
                return {"option_merge.addons": [], namespace: [ep1, ep2, ep3]}[ns]
            fake_iter_entry_points = mock.Mock(name="iter_entry_points", side_effect=iter_entry_points)

            with mock.patch("option_merge_addons.pkg_resources.iter_entry_points", fake_iter_entry_points):
                getter = AddonGetter()
                self.assertEqual(getter.entry_points, {"option_merge.addons": {}})
                getter.add_namespace(namespace)
                self.assertEqual(getter.entry_points, {"option_merge.addons": {}, namespace: {"entry1": [ep1], "entry2": [ep2, ep3]}})

            self.assertEqual(fake_iter_entry_points.mock_calls, [mock.call("option_merge.addons"), mock.call(namespace)])

    describe "all_for":
        it "yields nothing if we don't know about the namespace":
            self.assertEqual(list(AddonGetter().all_for("blah")), [])

        it "yields all known names for namespace":
            getter = AddonGetter()
            getter.entry_points["blah"] = {
                  "one": mock.Mock(name="one")
                , "two": mock.Mock(name='two')
                }
            self.assertEqual(sorted(getter.all_for("blah")), sorted([("blah", "one"), ("blah", "two")]))

    describe "get":
        before_each:
            self.getter = AddonGetter()
            self.configuration = mock.Mock(name="configuration")
            self.collector = mock.Mock(name="collector", configuration=self.configuration)

        it "Logs a warning and does nothing if namespace is unknown":
            assert "bob" not in self.getter.namespaces
            self.assertIs(self.getter("bob", "one", self.collector), None)

        it "finds all the entry points and resolved the into the addon_spec":
            known = mock.Mock(name="known")
            result = mock.Mock(name="result")
            normalised = mock.Mock(name="normalised")

            result_spec = mock.Mock(name='result_spec', spec=["normalise"])
            addon_spec = mock.Mock(name='addons_spec', spec=["normalise"])

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
            fake_resolve_entry_points = mock.Mock(name="resolve_entry_points", return_value=(resolver, extras))

            self.getter.add_namespace(namespace, result_spec, addon_spec)

            with mock.patch.multiple(self.getter, find_entry_points=fake_find_entry_points, resolve_entry_points=fake_resolve_entry_points):
                self.assertEqual(self.getter(namespace, entry_point_name, collector, known), normalised)

            addon_spec.normalise.assert_called_once_with(Meta({}, [])
                , {"namespace": namespace, "name": entry_point_name, "resolver": resolver, "extras": extras}
                )

            entry_point_full_name = "{0}.{1}".format(namespace, entry_point_name)
            fake_find_entry_points.assert_called_once_with(namespace, entry_point_name, entry_point_full_name)
            fake_resolve_entry_points.assert_called_once_with(namespace, entry_point_name, collector, mock.ANY, entry_points, entry_point_full_name, known)

            addon_spec.normalise.assert_called_once_with(mock.ANY, {"namespace": namespace, "name": entry_point_name, "resolver": resolver, "extras":extras})

            result_maker = fake_resolve_entry_points.mock_calls[0][1][3]
            self.assertIs(result_maker(blah="one"), result)
            result_spec.normalise.assert_called_once_with(mock.ANY, {"blah": "one"})

    describe "find_entry_points":
        before_each:
            self.namespace = mock.Mock(name="namesapce")
            self.entry_point_name = mock.Mock(name="entry_point_name")
            self.entry_point_full_name = "{0}.{1}".format(self.namespace, self.entry_point_name)

        it "uses pkg_resources.iter_entry_points":
            ep = mock.Mock(name="ep")
            ep.name = self.entry_point_name
            fake_iter_entry_points = mock.Mock(name="iter_entry_points", return_value=[ep])

            with mock.patch("option_merge_addons.pkg_resources.iter_entry_points", fake_iter_entry_points):
                res = AddonGetter()
                res.add_namespace(self.namespace)
                found = res.find_entry_points(self.namespace, self.entry_point_name, self.entry_point_full_name)
                self.assertEqual(found, [ep])

        it "complains if it finds no entry points":
            fake_iter_entry_points = mock.Mock(name="iter_entry_points", return_value=[])

            with self.fuzzyAssertRaisesError(AddonGetter.NoSuchAddon, addon=self.entry_point_full_name):
                with mock.patch("option_merge_addons.pkg_resources.iter_entry_points", fake_iter_entry_points):
                    res = AddonGetter()
                    res.add_namespace(self.namespace)
                    res.find_entry_points(self.namespace, self.entry_point_name, self.entry_point_full_name)

        it "uses all found entry points if it finds many":
            ep = mock.Mock(name="ep")
            ep.name = self.entry_point_name
            ep2 = mock.Mock(name="ep2")
            ep2.name = self.entry_point_name
            fake_iter_entry_points = mock.Mock(name="iter_entry_points", return_value=[ep, ep2])

            with mock.patch("option_merge_addons.pkg_resources.iter_entry_points", fake_iter_entry_points):
                res = AddonGetter()
                res.add_namespace(self.namespace)
                found = res.find_entry_points(self.namespace, self.entry_point_name, self.entry_point_full_name)
                self.assertEqual(found, [ep, ep2])

    describe "resolve_entry_points":
        before_each:
            self.namespace = mock.Mock(name="namespace")
            self.entry_point_name = mock.Mock(name="entry_point_name")
            self.collector = mock.Mock(name="collector")
            self.result_maker = mock.Mock(name="result_maker")

            self.module_name1 = self.unique_value()
            self.module_name2 = self.unique_value()
            self.ep1 = mock.Mock(name="ep1", module_name=self.module_name1)
            self.ep2 = mock.Mock(name="ep2", module_name=self.module_name2)
            self.entry_points = [self.ep1, self.ep2]
            self.entry_point_full_name = mock.Mock(name="entry_point_full_name")

            self.getter = AddonGetter()

        it "raises an error if it can't resolve any of the entry points":
            e1 = ImportError("nup")
            self.ep1.resolve.side_effect = e1
            self.ep1.resolve.return_value = {}

            found_error = AddonGetter.BadImport("Error whilst resolving entry_point", importing=self.entry_point_full_name, module=self.ep1.module_name, error=str(e1))

            with self.fuzzyAssertRaisesError(AddonGetter.BadImport, "Failed to import some entry points", _errors=[found_error]):
                self.getter.resolve_entry_points(self.namespace, self.entry_point_name, self.collector, self.result_maker, self.entry_points, self.entry_point_full_name, [])

        it "gets a resolver and returns it with the extras":
            self.ep1.resolve.return_value = type("module", (object, ), {"hook": option_merge_addon_hook(extras=[("one", "two")])(lambda *args, **kwargs: None)})
            self.ep2.resolve.return_value = type("module", (object, ), {})

            resolver = mock.Mock(name="resolver")
            fake_get_resolver = mock.Mock(name="get_resolver", return_value=resolver)

            hooks, extras = self.getter.resolve_entry_points(self.namespace, self.entry_point_name, self.collector, self.result_maker, self.entry_points, self.entry_point_full_name, [])
            with mock.patch.object(self.getter, "get_resolver", fake_get_resolver):
                res = self.getter.resolve_entry_points(self.namespace, self.entry_point_name, self.collector, self.result_maker, self.entry_points, self.entry_point_full_name, [])
                self.assertEqual(res, (resolver, extras))

    describe "get_hooks_and_extras":
        it "finds hooks from the modules":
            hook1 = lambda *args, **kwargs: None
            module1 = type("module", (object, ), {})
            module2 = type("module", (object, ), {"hook": option_merge_addon_hook()(hook1)})
            modules = [module1, module2]

            self.assertEqual(AddonGetter().get_hooks_and_extras(modules, []), ([module2.hook], []))

        it "can find multiple hooks from the modules":
            hook1 = lambda *args, **kwargs: None
            hook2 = lambda *args, **kwargs: None
            module1 = type("module", (object, ), {})
            module2 = type("module", (object, ), {"hook": option_merge_addon_hook()(hook1), "other": option_merge_addon_hook()(hook2), "not_a_hook": lambda: None})
            modules = [module1, module2]

            self.assertEqual(AddonGetter().get_hooks_and_extras(modules, []), ([module2.hook, module2.other], []))

        it "can find multiple hooks from multiple modules":
            hook1 = lambda *args, **kwargs: None
            hook2 = lambda *args, **kwargs: None
            hook3 = lambda *args, **kwargs: None
            module1 = type("module", (object, ), {"fasf": option_merge_addon_hook()(hook3)})
            module2 = type("module", (object, ), {"hook": option_merge_addon_hook()(hook1), "other": option_merge_addon_hook()(hook2), "not_a_hook": lambda: None})
            modules = [module1, module2]

            self.assertEqual(AddonGetter().get_hooks_and_extras(modules, []), ([module1.fasf, module2.hook, module2.other], []))

        it "finds extras from the hooks":
            hook1 = lambda *args, **kwargs: None
            hook2 = lambda *args, **kwargs: None
            hook3 = lambda *args, **kwargs: None
            module1 = type("module", (object, ), {"fasf": option_merge_addon_hook(extras=[("one", "two")])(hook3)})
            module2 = type("module", (object, ), {"hook": option_merge_addon_hook(extras=[("one", "three")])(hook1), "other": option_merge_addon_hook(extras=[("four", "five")])(hook2), "not_a_hook": lambda: None})
            modules = [module1, module2]

            self.assertEqual(AddonGetter().get_hooks_and_extras(modules, [])
                , ([module1.fasf, module2.hook, module2.other], [("one", "two"), ("one", "three"), ("four", "five")])
                )

        it "deals with __all__":
            hook1 = lambda *args, **kwargs: None
            module1 = type("module", (object, ), {"asdf": option_merge_addon_hook(extras=[("one", "one"), ("one", "__all__")])(hook1)})
            modules = [module1]

            all_pairs = [("one", "one"), ("one", "two"), ("one", "three"), ("one", "four")]
            all_for = mock.Mock(name="all_for", return_value=all_pairs)

            with mock.patch.object(AddonGetter, "all_for", all_for):
                self.assertEqual(
                      AddonGetter().get_hooks_and_extras(modules, [("one", "two")])
                    , ([module1.asdf], [("one", "one"), ("one", "four"), ("one", "three")])
                    )

            all_for.assert_called_once_with("one")

    describe "get_resolver":
        before_each:
            self.hooks = mock.Mock(name="hooks")
            self.collector = mock.Mock(name="collector")
            self.result_maker = mock.Mock(name="result_maker")

        it "returns a function":
            assert callable(AddonGetter().get_resolver(self.collector, self.result_maker, self.hooks))

        it "calls just the post_register hooks if post_register is True and also gives them the kwargs":
            called = []
            kw3 = mock.Mock(name="kw3")
            kw4 = mock.Mock(name="kw4")

            hook1 = option_merge_addon_hook(post_register=True)(lambda c, kw3, kw4: called.append((c, 1)))
            hook2 = option_merge_addon_hook(post_register=False)(lambda: called.append(2))
            hook3 = option_merge_addon_hook(post_register=True)(lambda c, kw3, kw4: called.append((c, 3)))
            hook4 = option_merge_addon_hook(post_register=False)(lambda: called.append(4))
            hooks = [hook1, hook2, hook3, hook4]

            resolver = AddonGetter().get_resolver(self.collector, self.result_maker, hooks)

            self.assertEqual(called, [])
            list(resolver(post_register=True, kw3=kw3, kw4=kw4))
            self.assertEqual(called, [(self.collector, 1), (self.collector, 3)])

        it "calls non post_register hooks if post_register is False and passes in the collector and result_maker":
            called = []

            hook1 = option_merge_addon_hook(post_register=True)(lambda c, kw3, kw4: called.append((c, 1)))
            hook2 = option_merge_addon_hook(post_register=False)(lambda c, r: called.append((c, r, 2)))
            hook3 = option_merge_addon_hook(post_register=True)(lambda c, kw3, kw4: called.append((c, 3)))
            hook4 = option_merge_addon_hook(post_register=False)(lambda c, r: called.append((c, r, 4)))
            hooks = [hook1, hook2, hook3, hook4]

            resolver = AddonGetter().get_resolver(self.collector, self.result_maker, hooks)

            self.assertEqual(called, [])
            list(resolver(post_register=False))
            self.assertEqual(called, [(self.collector, self.result_maker, 2), (self.collector, self.result_maker, 4)])
