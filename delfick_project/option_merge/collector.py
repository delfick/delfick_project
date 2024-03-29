"""
The collector object is responsible for collecting configuration
and setting up converters

For example:

.. code-block:: python

    class JsonCollector(Collector):
        def start_configuration(self):
            return MergedOptions()

        def find_missing_config(self, configuration):
            assert "important_option" in configuration

        def extra_prepare(self, configuration, args_dict):
            configuration.update(
                  {"some_option": args_dict["some_option"]}
                , source=<extra_prepare>
                )

        def read_file(self, location):
            return json.loads(location)

        def add_configuration(self, configuration, collect_another_source, done, result, src):
            configuration.update(result, source=src)
            for loc in result.get("others", []):
                collect_another_source(
                      os.path.join(os.path.dirname(src), loc)
                    , prefix=os.path.splitext(loc)[1]
                    )

        def extra_configuration_collection(self, configuration):
            def convert(p, v):
                return v * 2
            configuration.add_converter(
                  Converter(
                      convert=convert
                    , convert_path=["some", "contrived", "example"]
                    )
                )

    collector = JsonCollector()
    collector.prepare(
          "/path/to/first_config_file.json"
        , {"some_option": "stuff"}
        )

    #### /path/to/first_config_file.json
    # { "hello": "there"
    # , "others": ["some.json"]
    # }

    #### /path/to/some.json
    # { "some":
    #   { "contrived":
    #     { "example": 2
    #     }
    #   }
    # }

    collector.configuration["some_option"] == "stuff"
    collector.configuration["some.contrived.example"] == 4
"""

import json
import logging
import os
import tempfile
from contextlib import contextmanager
from getpass import getpass

from delfick_project.norms import Meta, sb

from .converter import Converter

log = logging.getLogger("delfick_project.option_merge.collector")


@contextmanager
def a_file(source):
    if isinstance(source, dict):
        filename = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, prefix="-internal-") as tmp:
                filename = tmp.name

            with open(filename, "w") as fle:
                fle.write(json.dumps(source))

            yield filename
        finally:
            if filename and os.path.exists(filename):
                os.remove(filename)
    else:
        yield source


class Collector(object):
    """
    When using the Collector, it is expected that you implement a number of hooks
    to make this class useful.
    """

    class BadFileErrorKls(Exception):
        _fake_delfick_error = True

        def __init__(self, message):
            self.message = message
            self.kwargs = {}

        def __str__(self):
            return f"BadFile: {self.message}"

    class BadConfigurationErrorKls(Exception):
        _fake_delfick_error = True

        def __init__(self, _errors):
            self.message = ""
            self.kwargs = {}
            self.errors = _errors

        def __str__(self):
            ss = []
            for error in self.errors:
                ss.append("\n\t".join(str(error).split("\n")))
            s = "\n\t".join(ss)
            message = f"errors:\n=======\n\n\t{s}"
            return f"BadConfiguration:\n{message}"

    def __init__(self):
        self.setup()

    ########################
    ###   HOOKS
    ########################

    def setup(self):
        """Called at __init__ time"""

    def alter_clone_args_dict(self, new_collector, new_args_dict, *args, **kwargs):
        """
        Hook for altering args_dict given to a clone collector it must return a dictionary

        This dictionary will be used in the ``prepare`` call for the new collector
        """
        return new_args_dict

    def find_missing_config(self, configuration):
        """Hook to raise errors about missing configuration"""

    def extra_prepare(self, configuration, args_dict):
        """Hook for any extra preparation before the converters are activated"""

    def extra_prepare_after_activation(self, configuration, args_dict):
        """Hook for any extra preparation after the converters are activated"""

    def home_dir_configuration_location(self):
        """Hook to return the location of the configuration in the user's home directory"""
        return None

    def read_file(self, location):
        """Hook to read in a file and return a dictionary"""
        raise NotImplementedError()

    def start_configuration(self):
        """Hook for starting the base of the configuration"""
        raise NotImplementedError()

    def add_configuration(self, configuration, collect_another_source, done, result, src):
        """
        Hook to add to the configuration the loaded result from src into configuration

        The collect_another_source function can be used to collect another source

        And done is a dictionary of configuration we have already added
        """
        raise NotImplementedError()

    def extra_configuration_collection(self, configuration):
        """Hook to do any extra configuration collection or converter registration"""

    ########################
    ###   USAGE
    ########################

    def clone(self, *args, **kwargs):
        """Create a new collector that is a clone of this one"""
        if not hasattr(self, "configuration_file"):
            return self.__class__()
        new_collector = self.__class__()
        args_dict_clone = dict(self.configuration["args_dict"].items())
        new_args_dict = self.alter_clone_args_dict(new_collector, args_dict_clone, *args, **kwargs)
        new_collector.prepare(self.configuration_file, new_args_dict)
        return new_collector

    def prepare(self, configuration_file, args_dict, extra_files=None):
        """
        Prepare the collector!

        * Collect all the configuration
        * find missing configuration
        * do self.extra_prepare
        * Activate the converters
        * Do self.extra_prepare_after_activation
        """
        self.configuration_file = configuration_file
        self.configuration = self.collect_configuration(
            configuration_file, args_dict, extra_files=extra_files
        )

        self.find_missing_config(self.configuration)

        self.extra_prepare(self.configuration, args_dict)
        self.configuration.converters.activate()
        self.extra_prepare_after_activation(self.configuration, args_dict)

    def register_converters(self, specs, configuration=None, announce_converters=True):
        """
        Register converters

        specs
            a Dictionary of {key: spec}

            Where key is either a string or a tuple of strings

            You would use a tuple of strings if you want to have a nested key,
            which is useful if any part of the key has dots in it.

            For example ``("images", "ubuntu.16.04")``

        configuration
            The configuration to add the converter to.

            This defaults to self.configuration

        announce_converters
            If True (default) then we log when we convert these keys

        For example:

        .. code-block:: python

            collector.register_converters({
                "one": sb.string_spec(),
                ("two", "three"): sb.integer_spec()
            })
        """
        if configuration is None:
            configuration = self.configuration

        s = sb.dictof(sb.tupleof(sb.string_spec()), sb.any_spec())
        specs = s.normalise(Meta.empty().at("<register_converters>"), specs)

        for key, spec in specs.items():

            def make_converter(k, s):
                def converter(p, v):
                    if announce_converters:
                        log.info("Converting %s", p)

                    meta = Meta(p.configuration, [])
                    for kk in k:
                        meta = meta.at(kk)
                    configuration.converters.started(p)
                    return s.normalise(meta, v)

                configuration.add_converter(Converter(convert=converter, convert_path=k))
                if k not in configuration:
                    configuration[k] = sb.NotSpecified

            make_converter(key, spec)

    ########################
    ###   CONFIG
    ########################

    def collect_configuration(self, configuration_file, args_dict, extra_files=None):
        """Return us a MergedOptions with this configuration and any collected configurations"""
        errors = []

        configuration = self.start_configuration()

        configuration.update(
            {"getpass": getpass, "collector": self, "args_dict": args_dict}, source="<preparation>"
        )

        sources = []
        if configuration_file:
            sources.append(configuration_file)

        if extra_files:
            sources.extend(extra_files)

        home_dir_configuration = self.home_dir_configuration_location()
        if home_dir_configuration:
            sources.insert(0, home_dir_configuration)

        done = set()

        def add_configuration(src, prefix=None, extra=None):
            log.info("Adding configuration from %s", os.path.abspath(src))
            if os.path.abspath(src) in done:
                return
            else:
                done.add(os.path.abspath(src))

            if src is None or not os.path.exists(src):
                return

            try:
                if os.stat(src).st_size == 0:
                    result = {}
                else:
                    result = self.read_file(src)
            except self.BadFileErrorKls as error:
                errors.append(error)
                return

            if not result:
                return

            if extra:
                result.update(extra)
            result["config_root"] = os.path.abspath(os.path.dirname(src))

            while prefix:
                part = prefix.pop()
                result = {part: result}

            self.add_configuration(configuration, add_configuration, done, result, src)

        for source in sources:
            with a_file(source) as source:
                add_configuration(source)

        self.extra_configuration_collection(configuration)

        if errors:
            raise self.BadConfigurationErrorKls(
                "Some of the configuration was broken", _errors=errors
            )

        return configuration
