from setuptools import setup, find_packages
from delfick_project import VERSION

# fmt: off

setup(
      name = 'delfick_project'
    , version = VERSION
    , packages = find_packages(include="delfick_project.*", exclude=["tests*"])

    , python_requires = ">= 3.6"

    , extras_require =
      { 'tests':
        [ 'pytest>=7.0.1'
        , 'noseOfYeti>=2.3.1'
        , 'rainbow_logging_handler==2.2.2'
        ]
      }

    , author = 'Stephen Moore'
    , license = 'MIT'
    , author_email = 'github@delfick.com'

    , url = "https://github.com/delfick/delfick_project"
    , description = 'Common code I use in all my projects'
    , long_description = open("README.rst").read()
    )

# fmt: on
