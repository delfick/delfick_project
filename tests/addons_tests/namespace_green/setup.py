from namespace_green import VERSION
from setuptools import setup

setup(
      name = "namespace_green"
    , version = VERSION
    , packages = ['namespace_green']

    , entry_points =
      { "green.addons":
        [ "one = namespace_green.one"
        , "two = namespace_green.two"
        , "three = namespace_green.three"
        , "four = namespace_green.four"
        , "five = namespace_green.five"
        , "six = namespace_green.six"
        , "seven = namespace_green.seven"
        , "eight = namespace_green.eight"
        , "nine = namespace_green.nine"
        , "ten = namespace_green.ten"
        ]
      }
    )

