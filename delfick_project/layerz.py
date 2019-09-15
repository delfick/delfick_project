"""
A simple module for creating layers of dependencies.

.. code-block:: python

    from delfick_project.layerz import Layers

    dep1 = type("dep1", (object, ), {"dependencies": lambda s, all_deps: []})()
    dep2 = type("dep2", (object, ), {"dependencies": lambda s, all_deps: ["dep3"]})()
    dep3 = type("dep3", (object, ), {"dependencies": lambda s, all_deps: ["dep1"]})()
    dep4 = type("dep4", (object, ), {"dependencies": lambda s, all_deps: ["dep3"]})()
    dep5 = type("dep1", (object, ), {"dependencies": lambda s, all_deps: ["dep4", "dep2"]})()

    layers = Layers({"dep1": dep1, "dep2": dep2, "dep3": dep3, "dep4": dep4, "dep5": dep5})
    layers.add_to_layers("dep5")
    for layer in layers.layered:
        # might get something like
        # [("dep5", dep5)]
        # [("dep4", dep4), ("dep2", dep2)]
        # [("dep3", dep3)]
        # [("dep1", dep1)]

When we create the layers, it will do a depth first addition of all dependencies
and only add a dep to a layer that occurs after all it's dependencies.

Cyclic dependencies will be complained about.
"""

from delfick_project.errors import DelfickError


class DepCycle(DelfickError):
    pass


class Layers(object):
    def __init__(self, deps, all_deps=None):
        self.deps = deps
        self.all_deps = all_deps
        if self.all_deps is None:
            self.all_deps = deps

        self.accounted = {}
        self._layered = []

    def reset(self):
        """Make a clean slate (initialize layered and accounted on the instance)"""
        self.accounted = {}
        self._layered = []

    @property
    def layered(self):
        """Yield list of [[(name, dep), ...], [(name, dep), ...], ...]"""
        result = []
        for layer in self._layered:
            nxt = []
            for name in layer:
                nxt.append((name, self.all_deps[name]))
            result.append(nxt)
        return result

    def add_all_to_layers(self):
        """Add all the deps to layered"""
        for dep in sorted(self.deps):
            self.add_to_layers(dep)

    def add_to_layers(self, name, chain=None):
        layered = self._layered

        if name not in self.accounted:
            self.accounted[name] = True
        else:
            return

        if chain is None:
            chain = []
        chain = chain + [name]

        for dependency in sorted(self.all_deps[name].dependencies(self.all_deps)):
            dep_chain = list(chain)
            if dependency in chain:
                dep_chain.append(dependency)
                raise DepCycle(chain=dep_chain)
            self.add_to_layers(dependency, dep_chain)

        layer = 0
        for dependency in self.all_deps[name].dependencies(self.all_deps):
            for index, deps in enumerate(layered):
                if dependency in deps:
                    if layer <= index:
                        layer = index + 1
                    continue

        if len(layered) == layer:
            layered.append([])
        layered[layer].append(name)
