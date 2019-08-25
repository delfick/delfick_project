from setuptools import setup, find_packages
from delfick_project import VERSION

# fmt: off

setup(
      name = 'delfick_project'
    , version = VERSION
    , packages = find_packages(include="delfick_project.*", exclude=["tests*"])

    , python_requires = ">= 3.4"

    , install_requires =
      [ 'rainbow_logging_handler==2.2.2'
      , 'namedlist==1.7'
      ]

    , extras_require =
      { 'tests':
        [ 'pytest==5.1.1'
        , 'noseOfYeti==1.8.3'
        ]
      }

    , author = 'Stephen Moore'
    , license = 'MIT'
    , author_email = 'delfick755@gmail.com'

    , url = "https://github.com/delfick/delfick_project"
    , description = 'Common code I use in all my projects'
    , long_description = open("README.rst").read()
    )

# fmt: on
