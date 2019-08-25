from delfick_project.errors import BadSpecValue, dictobj, sb, Meta
from delfick_project.errors import DelfickError, ProgrammerError
from delfick_project.layerz import Layers

from collections import defaultdict
from operator import itemgetter
import pkg_resources
import logging
import six

log = logging.getLogger("delfick_project.addons")

class addon_hook(object):
    def __init__(self, extras=sb.NotSpecified, post_register=False):
        self.post_register = post_register
        if post_register and extras not in (None, {}, sb.NotSpecified):
            msg = "Sorry, can't specify ``extras`` and ``post_register`` at the same time"
            raise ProgrammerError(msg)
        spec = sb.listof(sb.tuple_spec(sb.string_spec(), sb.listof(sb.string_spec())))
        self.extras = spec.normalise(Meta({}, []), extras)

    def __call__(self, func):
        func.extras = self.extras
        func._delfick_project_addon_entry = True
        func._delfick_project_addon_entry_post_register = self.post_register
        return func

class spec_key_spec(sb.Spec):
    """
    Turns value into (int, (str1, str2, ..., strn))

    If value is a single string: (0, (val, ))

    if value is a tuple of strings: (0, (val1, val2, ..., valn))

    if value is a list of strings: (0, (val2, val2, ..., valn))

    if value is already correct, then return as is
    """
    def normalise_filled(self, meta, val):
        if isinstance(val, six.string_types):
            return (0, (val, ))
        else:
            if isinstance(val, list) or isinstance(val, tuple) and len(val) > 0:
                is_int = type(val[0]) is int
                is_digit = getattr(val[0], "isdigit", lambda: False)()
                if not is_int and not is_digit:
                    val = (0, val)

            spec = sb.tuple_spec(sb.integer_spec(), sb.tupleof(sb.string_spec()))
            return spec.normalise(meta, val)

class no_such_key_spec(sb.Spec):
    def setup(self, reason):
        self.reason = reason

    def normalise_filled(self, meta, val):
        raise BadSpecValue(self.reason, meta=meta)

class Result(dictobj.Spec):
    specs = dictobj.Field(sb.dictof(spec_key_spec(), sb.has("normalise")))
    extra = dictobj.Field(no_such_key_spec("Use extras instead (notice the s!)"))
    extras = dictobj.Field(sb.listof(sb.tuple_spec(sb.string_spec(), sb.tupleof(sb.string_spec()))))

class Addon(dictobj.Spec):
    name = dictobj.Field(sb.string_spec)
    extras = dictobj.Field(sb.listof(sb.tuple_spec(sb.string_spec(), sb.string_spec())))
    resolver = dictobj.Field(sb.any_spec)
    namespace = dictobj.Field(sb.string_spec)

    class BadHook(DelfickError):
        desc = "Bad Hook"

    @property
    def resolved(self):
        errors = []
        if getattr(self, "_resolved", None) is None:
            try:
                self._resolved = list(self.resolver())
            except Exception as error:
                errors.append(self.BadHook("Failed to resolve a hook", name=self.name, namespace=self.namespace, error=str(error)))

        if errors:
            raise self.BadHook(_errors=errors)

        return self._resolved

    def process(self, collector):
        for result in self.resolved:
            if collector is not None:
                collector.register_converters(
                      result.get("specs", {})
                    , Meta, collector.configuration, sb.NotSpecified
                    )

    def post_register(self, **kwargs):
        list(self.resolver(post_register=True, **kwargs))

    def unresolved_dependencies(self):
        for namespace, name in self.extras:
            yield (namespace, name)

    def resolved_dependencies(self):
        for result in self.resolved:
            for namespace, names in result.get("extras", []):
                if not isinstance(names, (tuple, list)):
                    names = (names, )
                for name in names:
                    yield (namespace, name)

    def dependencies(self, all_deps):
        for dep in self.unresolved_dependencies():
            yield dep
        if hasattr(self, "_resolved"):
            for dep in self.resolved_dependencies():
                yield dep

class AddonGetter(object):
    class NoSuchAddon(DelfickError):
        desc = "No such addon"
    class BadImport(DelfickError):
        desc = "Bad import"
    class BadAddon(DelfickError):
        desc = "Bad addon"

    def __init__(self):
        self.namespaces = {}
        self.entry_points = {}
        self.add_namespace("delfick_project.addons")

    def add_namespace(self, namespace, result_spec=None, addon_spec=None):
        self.namespaces[namespace] = (result_spec or Result.FieldSpec(), addon_spec or Addon.FieldSpec())
        self.entry_points[namespace] = defaultdict(list)
        for e in pkg_resources.iter_entry_points(namespace):
            self.entry_points[namespace][e.name].append(e)

    def all_for(self, namespace):
        if namespace not in self.entry_points:
            log.warning("Unknown plugin namespace\tnamespace=%s", namespace)
            return

        for name in self.entry_points[namespace]:
            yield (namespace, name)

    def __call__(self, namespace, entry_point_name, collector, known=None):
        if namespace not in self.namespaces:
            log.warning("Unknown plugin namespace\tnamespace=%s\tentry_point=%s\tavailable=%s"
                , namespace, entry_point_name, sorted(self.namespaces.keys())
                )
            return

        entry_point_full_name = "{0}.{1}".format(namespace, entry_point_name)

        entry_points = self.find_entry_points(
              namespace, entry_point_name, entry_point_full_name
            )

        def result_maker(**data):
            return self.namespaces[namespace][0].normalise(Meta(data, []), data)

        resolver, extras = self.resolve_entry_points(
                namespace, entry_point_name, collector
              , result_maker, entry_points, entry_point_full_name
              , known
              )

        return self.namespaces[namespace][1].normalise(Meta({}, [])
            , { "namespace": namespace
              , "name": entry_point_name
              , "resolver": resolver
              , "extras": extras
              }
            )

    def find_entry_points(self, namespace, entry_point_name, entry_point_full_name):
        it = self.entry_points[namespace][entry_point_name]
        entry_points = list(it)

        if len(entry_points) > 1:
            log.warning("Found multiple entry_points for {0}".format(
              entry_point_full_name
            ))
        elif len(entry_points) == 0:
            raise self.NoSuchAddon(addon=entry_point_full_name)
        else:
            log.info("Found {0} addon".format(entry_point_full_name))

        return entry_points

    def resolve_entry_points(self
        , namespace, entry_point_name, collector
        , result_maker, entry_points, entry_point_full_name
        , known
        ):
        errors = []
        modules = []
        for entry_point in entry_points:
            try:
                modules.append(entry_point.resolve())
            except ImportError as error:
                err = self.BadImport("Error whilst resolving entry_point"
                    , importing=entry_point_full_name
                    , module=entry_point.module_name
                    , error=str(error)
                    )
                errors.append(err)

        if errors:
            raise self.BadImport("Failed to import some entry points"
                , _errors=errors
                )

        hooks, extras = self.get_hooks_and_extras(modules, known)
        resolver = self.get_resolver(collector, result_maker, hooks)
        return resolver, extras

    def get_hooks_and_extras(self, modules, known):
        found = []
        extras = []
        for module in modules:
            for attr in dir(module):
                hook = getattr(module, attr)
                if getattr(hook, "_delfick_project_addon_entry", False):
                    found.append(hook)
                    for namespace, names in hook.extras:
                        for name in names:
                            pairs = [(namespace, name)]
                            if name == "__all__":
                                pairs = sorted([pair for pair in self.all_for(namespace) if pair not in known])
                            for pair in pairs:
                                if pair not in extras:
                                    extras.append(pair)
        return found, extras

    def get_resolver(self, collector, result_maker, hooks):
        def resolve(post_register=False, **kwargs):
            for hook in hooks:
                is_post_register = getattr(hook, "_delfick_project_addon_entry_post_register", False)
                if (post_register and not is_post_register) or (is_post_register and not post_register):
                    continue

                if post_register:
                    hook(collector, **kwargs)
                else:
                    r = hook(collector, result_maker)
                    if r is not None:
                        yield r

        return resolve

class Register(object):
    """
    Responsible for finding and registering addons.

    Addons can register unresolved dependencies and resolved dependencies.

    The difference is that an unresolved dependency does not involve executing
    the addon, whereas a resolved dependency does.

    Order is such that:
        * import known pairs
        * import extra pairs from known pairs
        * resolve known and extra pairs in layers
        * import and resolve extra pairs from those layers until no more are known
        * call post_register on all pairs in layers

    Usage:

    .. code-block:: python

        register = Register(AddonGetter, collector)

        # Add pairs as many times as you want
        register.add_pairs(("namespace1", "name1"), ("namespace2", "name2"), ..., )
        register.add_pairs(("namespace1", "name1"), ("namespace2", "name2"), ..., )

        # Now we import but not resolve the addons to get the unresolved extras
        register.recursive_import_known()

        # We now have a record of all the unresolved extras to be imported
        # Let's actually call our addons
        # And in the process, import and resolve any resolved extras
        register.recursive_resolve_imported()

        # Finally, everything has been imported and resolved, let's call post_register
        register.post_register({namespace1: {arg1=val1, arg2=val2}, ...})

    Alternatively if you don't want that much control:

    .. code-block:: python

        register = Register(AddonGetter, collector)
        register.register((namespace1, name1), (namespace2, name2), ...
            , namespace1={arg1:val1}, namespace2 = {arg1=val1}
            )

        # This will ensure the same resolution path as the manual approach
    """
    def __init__(self, addon_getter, collector):
        self.known = []
        self.imported = {}
        self.resolved = {}
        self.collector = collector
        self.addon_getter = addon_getter

    ########################
    ###   AUTO USAGE
    ########################

    def register(self, *pairs, **extra_args):
        self.add_pairs(*pairs)
        self.recursive_import_known()
        self.recursive_resolve_imported()
        self.post_register(extra_args)

    ########################
    ###   MANUAL USAGE
    ########################

    def add_pairs(self, *pairs):
        import_all = set()
        found = []
        for pair in pairs:
            if pair[1] == "__all__":
                import_all.add(pair[0])
            elif pair not in self.known:
                found.append(pair)
                self.known.append(pair)

        for namespace in import_all:
            for pair in self.addon_getter.all_for(namespace):
                if pair not in self.known:
                    found.append(pair)
                    self.known.append(pair)

        return found

    def recursive_import_known(self):
        added = False
        while True:
            nxt = self._import_known()
            if not nxt:
                break
            added = nxt or added
        return added

    def recursive_resolve_imported(self):
        while True:
            if not self._resolve_imported():
                break

    def post_register(self, extra_args=None):
        for layer in self.layered:
            for pair, imported in layer:
                args = (extra_args or {}).get(pair[0], {})
                imported.post_register(**args)

    ########################
    ###   LAYERED
    ########################

    @property
    def layered(self):
        layers = Layers(self.imported)
        for key in sorted(self.imported):
            layers.add_to_layers(key)
        for layer in layers.layered:
            yield layer

    ########################
    ###   HELPERS
    ########################

    def _import_known(self):
        added = False
        for pair in list(self.known):
            namespace, name = pair
            if pair not in self.imported:
                imported = self.addon_getter(namespace, name, self.collector, known=list(self.known))
                if imported is None:
                    self.known.pop(self.known.index(pair))
                else:
                    self.imported[pair] = imported
                    self.add_pairs_from_extras(imported.extras)
                    added = True
        return added

    def _resolve_imported(self):
        for layer in self.layered:
            for pair, imported in layer:
                namespace, name = pair
                if pair not in self.resolved:
                    self.resolved[pair] = list(imported.resolved)
                    imported.process(self.collector)
                    for result in imported.resolved:
                        found = self.add_pairs_from_extras(result.extras)
                        if any("__all__" in names for _, names in result.extras):
                            want = defaultdict(list)
                            for namespace, names in result.extras:
                                for name in names:
                                    if name != "__all__":
                                        want[namespace].append(name)

                            for namespace, name in found:
                                want[namespace].append(name)

                            result.extras = sorted([
                                (namespace, tuple(sorted(set(names))))
                                for namespace, names in sorted(want.items())
                            ])

        return self.recursive_import_known()

    def add_pairs_from_extras(self, extras):
        found = []
        for pair in extras:
            namespace, names = pair
            if not isinstance(names, (tuple, list)):
                names = (names, )

            for name in names:
                found.extend(self.add_pairs((namespace, name)))
        return sorted(found)
