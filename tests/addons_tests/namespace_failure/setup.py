from namespace_failure import VERSION
from setuptools import setup

setup(
      name = "namespace_failure"
    , version = VERSION
    , packages = ['namespace_failure']

    , entry_points =
      { "failure.addons":
        [ "unimportable = namespace_failure.unimportable"
        , "nohook = namespace_failure.nohook"
        , "noresult = namespace_failure.noresult"
        , "postregister_and_extras = namespace_failure.postregister_and_extras"
        , "recursive1 = namespace_failure.recursive1"
        , "recursive2 = namespace_failure.recursive2"
        , "recursive1_extra = namespace_failure.recursive1_extra"
        , "recursive2_extra = namespace_failure.recursive2_extra"
        , "bad_hook = namespace_failure.bad_hook"
        ]
      }
    )

