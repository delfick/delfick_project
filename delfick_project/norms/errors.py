"""
These errors are all importable from ``delfick_project.norms``

For example:

.. code-block::

    from delfick_project.norms import BadSpecValue
"""
from delfick_project.errors import DelfickError


class BadSpec(DelfickError):
    """.. autoattribute:: desc"""

    desc = "Something wrong with this specification"


class BadSpecValue(BadSpec):
    """.. autoattribute:: desc"""

    desc = "Bad value"


class BadDirectory(BadSpecValue):
    """.. autoattribute:: desc"""

    desc = "Expected a path to a directory"


class BadFilename(BadSpecValue):
    """.. autoattribute:: desc"""

    desc = "Expected a path to a filename"


class DeprecatedKey(BadSpecValue):
    """.. autoattribute:: desc"""

    desc = "Key is deprecated"


class BadSpecDefinition(BadSpecValue):
    """.. autoattribute:: desc"""

    desc = "Spec isn't defined so well"
