"""
``Meta`` is an important object that is used to keep track of our position in
the original ``val`` when we are normalising it.
"""
class Meta(object):
    """
    Meta has a concept of the wider context, kept as the ``everything`` property
    , and the path into ``everything`` where we are.

    We move around the ``everything`` by creating new instances of ``Meta`` that
    refers to a new part: using the methods on the ``meta`` object.

    Arguments
        everything
            The wider context

        path
            Can be given as a string or a list of tuples.

            If provided as a string, it is converted to ``[(path, "")]``

    Usage
        .. automethod:: at

        .. automethod:: indexed_at

        .. automethod:: key_names

    Useful
        .. automethod:: __eq__

        .. automethod:: __lt__

        .. automethod:: __gt__

    Path
        .. automethod:: path

        .. automethod:: nonspecial_path

        .. automethod:: source
    """
    everything = None

    @classmethod
    def empty(kls):
        return kls({}, [])

    def __init__(self, everything, path):
        self._path = path
        if isinstance(self._path, str):
            self._path = [(self._path, "")]

        self.everything = everything

    def indexed_at(self, index):
        """
        Return a new instance with ``("", "[index]")`` added to the path
        """
        return self.new_path([("", "[{0}]".format(index))])

    def at(self, val):
        """
        Return a new instance with ``(path, "")`` added to the path
        """
        return self.new_path([(val, "")])

    def new_path(self, part):
        """Return a new instance of this class with additional path part"""
        return self.__class__(self.everything, self._path + part)

    def key_names(self):
        """Return {_key_name_<i>: <i'th part of part} for each part in the path reversed"""
        return dict(("_key_name_{0}".format(index), val) for index, (val, _) in enumerate(reversed(self._path)))

    def __eq__(self, other):
        """Wortk out if we have the same ``everything`` and ``path``"""
        return self.everything == other.everything and self.path == other.path

    def __lt__(self, other):
        """
        Work out if the ``str(everything) < str(other.everything)``
        and ``path < other.path``.
        """
        everything = self.everything
        if type(everything) is dict:
            everything = str(everything)

        other_everything = other.everything
        if type(other_everything) is dict:
            other_everything = str(other_everything)
        return everything < other_everything and self.path < other.path

    def __gt__(self, other):
        """Work out if we are not equal or less than other"""
        return self != other and not self < other

    @property
    def path(self):
        """Return the path as a string"""
        complete = []
        for part in self._path:
            if isinstance(part, str):
                name, extra = part, ""
            else:
                name, extra = part

            if name and complete:
                complete.append(".")
            if name or extra:
                complete.append("{0}{1}".format(name, extra))
        return "".join(complete)

    @property
    def nonspecial_path(self):
        """Return the path as a string without extra strings"""
        return ".".join(part for part, _ in self._path if part)

    @property
    def source(self):
        """
        Return the source path of this value
        by asking everything for the source of this path
        """
        if not hasattr(self.everything, "source_for"):
            return "<unknown>"
        else:
            try:
                return self.everything.source_for(self.nonspecial_path)
            except KeyError:
                return "<unknown>"

    def delfick_error_format(self, key):
        """Format a string for display in a delfick error"""
        if self.source in (None, "<unknown>") or self.source == []:
            return "{{path={0}}}".format(self.path)
        else:
            return "{{source={0}, path={1}}}".format(self.source, self.path)
