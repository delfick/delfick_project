class DepCycle(Exception):
    _fake_delfick_error = True
    def __init__(self, chain):
        self.message = ""
        self.chain = chain
        self.kwargs = dict(chain=chain)

    def __str__(self):
        return "DepCycle: chain={0}".format(self.chain)

class Layers(object):
    DepCycle = DepCycle

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
                raise self.DepCycle(chain=dep_chain)
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
