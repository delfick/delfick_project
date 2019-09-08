from namespace_blue import VERSION
from setuptools import setup

# fmt: off

setup(
      name = "namespace_blue"
    , version = VERSION
    , packages = ['namespace_blue']

    , entry_points =
      { "blue.addons":
        [ "one = namespace_blue.one"
        , "two = namespace_blue.two"
        , "three = namespace_blue.three"
        , "four = namespace_blue.four"
        , "five = namespace_blue.five"
        , "six = namespace_blue.six"
        ]
      }
    )

# fmt: on
