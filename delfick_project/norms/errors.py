from delfick_project.errors import DelfickError


class BadSpec(DelfickError):
    desc = "Something wrong with this specification"


class BadSpecValue(BadSpec):
    desc = "Bad value"


class BadDirectory(BadSpecValue):
    desc = "Expected a path to a directory"


class BadFilename(BadSpecValue):
    desc = "Expected a path to a filename"


class DeprecatedKey(BadSpecValue):
    desc = "Key is deprecated"


class BadSpecDefinition(BadSpecValue):
    desc = "Spec isn't defined so well"
