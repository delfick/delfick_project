from namespace_black import VERSION
from setuptools import setup

setup(
      name = "namespace_black"
    , version = VERSION
    , packages = ['namespace_black']

    , entry_points =
      { "black.addons":
        [ "one = namespace_black.one"
        , "two = namespace_black.two"
        , "three = namespace_black.three"
        , "four = namespace_black.four"
        , "five = namespace_black.five"
        , "six = namespace_black.six"
        , "seven = namespace_black.seven"
        , "eight = namespace_black.eight"
        , "nine = namespace_black.nine"
        , "ten = namespace_black.ten"
        ]
      }
    )

