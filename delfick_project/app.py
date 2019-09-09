"""
delfick_project provides an App class that helps with some of the plumbing
involved in making a cli application.

To use, define a subclass of App, fill out atleast execute and use the main
classmethod on it as the entry point to your application:

.. automethod:: App.main

The class is as follows:

.. autoclass:: App
"""
from .logging import setup_logging, setup_logging_theme
from .errors import DelfickError, UserQuit

import logging.handlers
import argparse
import logging
import sys
import os


class Ignore(object):
    pass


class BadOption(DelfickError):
    desc = "Bad option"


class CouldntKill(DelfickError):
    desc = "Bad process"


class ArgumentError(DelfickError):
    desc = "Bad cli argument"


########################
###   APP
########################


class App(object):
    """
    .. autoattribute:: VERSION

        The version of your application, best way is to define this somewhere
        and import it into your mainline and setup.py from that location

    .. autoattribute:: CliParserKls

        The class to use for our CliParser

    .. autoattribute:: logging_handler_file

        The file to log output to (default is stderr)

    .. autoattribute:: cli_categories

        self.execute is passed a dictionary args_dict which is from looking
        at the args_obj object returned by argparse

        This option will break up arguments into hierarchies based on the
        name of the argument.

        For example:

        ``cli_categories = ['app']``

        and we have arguments for
        ``[silent, verbose, debug, app_config, app_option1, app_option2]``

        Then args_dict will be:

        .. code-block:: json

            { "app":
                { "config": "value"
                , "option1": "value"
                , "option2": "value"
                }
            , "silent": "value"
            , "verbose": "value"
            , "debug": "value"
            }

    .. autoattribute:: cli_description

        The description to give at the top of ``--help`` output

    .. autoattribute:: cli_environment_defaults

        A map of environment variables to ``--argument`` that you want to map

        For example:

        ``cli_environment_defaults = {"APP_CONFIG": "--config"}``

        Items may also be a tuple of ``(replacement, default)``

        For example, ``{"APP_CONFIG": ("--config", "./config.yml")}``

        Which means ``defaults["--config"] == {'default': "./config.yml"}``
        if APP_CONFIG isn't in the environment.

    .. autoattribute:: cli_positional_replacements

        A list mapping positional arguments to ``--arguments``

        For example:

        ``cli_positional_replacements = ['--environment', '--stack']``
        Will mean the first positional argument becomes the value for
        ``--environment`` and the second positional becomes the value for
        ``--stack``

        Note for this to work, you must do something like:

        .. code-block:: python

            def setup_other_args(self, parser, defaults):
                parser.add_argument('--environment'
                    , help = "the environment!"
                    , **defaults['--environment']
                    )

        Items in positional_replacements may also be a tuple of
        ``(replacement, default)``

        For example:

        ``cli_positional_replacements = [('--task', 'list_tasks')]``
            will mean the first positional argument becomes the value for
            ``--task``

            But if it's not specified, then
            ``defaults['--task'] == {"default": "list_tasks"}``

    .. autoattribute:: issue_tracker_link

        A link to where users can go to post issues

        It is used when we get an unexpected exception.

    Hooks
        .. automethod:: execute

        .. automethod:: setup_other_logging

        .. automethod:: specify_other_args

        .. automethod:: exception_handler

    Customize
        .. automethod:: setup_logging_theme

    Default cli arguments
        ``--verbose`` ``--silent`` ``--debug``
            These control the level of logging in your application. Note that
            you may only specify one of these three.

            ``--silent`` means Errors only. ``--verbose`` and ``--debug`` do
            the same thing and just means we get DEBUG logs as well.
            
            If none of these three are specified then you'll get INFO and above
            logs.

        Logging options
            There are some options that are passed into
            :func:`~delfick_project.logging.setup_logging`

            * ``--logging-program``
            * ``--tcp-logging-address``
            * ``--udp-logging-address``
            * ``--syslog-address``
            * ``--json-console-logs``

        ``--version``
            Print out the version and quit
    """

    ########################
    ###   SETTABLE PROPERTIES
    ########################

    VERSION = Ignore
    issue_tracker_link = None

    CliParserKls = property(lambda s: CliParser)
    logging_handler_file = property(lambda s: sys.stderr)

    cli_categories = None
    cli_description = "My amazing app"
    cli_environment_defaults = None
    cli_positional_replacements = None

    ########################
    ###   USAGE
    ########################

    @classmethod
    def main(kls, argv=None, **execute_args):
        """
        Instantiates this class and calls the mainline

        Usage is intended to be:

        .. code-block:: python

            from delfick_project.app import App

            class MyApp(App):
                def execute(self, args_obj, args_dict, extra_args, logging_handler, **kwargs):
                    print("My wonderful program goes here!")

            main = MyApp.main
        """
        app = kls()
        app.mainline(argv, **execute_args)

    def execute(self, args_obj, args_dict, extra_args, logging_handler, **kwargs):
        """
        Hook for executing the application itself

        args_obj
            The object from argparse.parse_args

        args_dict
            The options for args_obj as a dictionary

        extra_args
            A string of everything specified after a ``--`` on the cli.

        logging_handler
            The logging handler created by setup_logging 

        kwargs
            Extra keyword arguments passed down from the mainline.
        """
        raise NotImplementedError()

    def setup_other_logging(self, args_obj, verbose=False, silent=False, debug=False):
        """
        Hook for setting up any other logging configuration

        For example:

        .. code-block:: python

            def setup_other_logging(self, args_obj, verbose, silent, debug):
                logging.getLogger("requests").setLevel([logging.CRITICAL, logging.ERROR][verbose or debug])
                logging.getLogger("paramiko.transport").setLevel([logging.CRITICAL, logging.ERROR][verbose or debug])
        """

    def specify_other_args(self, parser, defaults):
        """
        Hook for adding more arguments to the argparse Parser

        For example:

        .. code-block:: python

            def specify_other_args(self, parser, defaults):
                parser.add_argument("--special"
                    , help = "taste the rainbow"
                    , action = "store_true"
                    )
        """

    ########################
    ###   INTERNALS
    ########################

    def mainline(self, argv=None, print_errors_to=sys.stdout, **execute_args):
        """
        The mainline for the application

        * Initialize parser and parse argv
        * Initialize the logging
        * run self.execute()
        * Catch and display DelfickError
        * Display traceback if we catch an error and args_obj.debug
        """
        cli_parser = None
        args_obj, args_dict, extra_args = None, None, None
        try:
            cli_parser = self.make_cli_parser()
            try:
                args_obj, args_dict, extra_args = cli_parser.interpret_args(
                    argv, self.cli_categories
                )
                if args_obj.version:
                    print(self.VERSION)
                    return

                handler = self.setup_logging(args_obj)
                self.execute(args_obj, args_dict, extra_args, handler, **execute_args)
            except KeyboardInterrupt:
                if cli_parser and cli_parser.parse_args(argv)[0].debug:
                    raise
                raise UserQuit()
            except:
                self.exception_handler(sys.exc_info(), args_obj, args_dict, extra_args)
                raise
        except DelfickError as error:
            print("", file=print_errors_to)
            print("!" * 80, file=print_errors_to)
            print(
                "Something went wrong! -- {0}".format(error.__class__.__name__),
                file=print_errors_to,
            )
            print("\t{0}".format(error), file=print_errors_to)
            if cli_parser and cli_parser.parse_args(argv)[0].debug:
                raise
            sys.exit(1)
        except Exception:
            msg = "Something unexpected happened!! Please file a ticket in the issue tracker! {0}".format(
                self.issue_tracker_link
            )
            print("\n\n{0}\n{1}\n".format(msg, "=" * len(msg)))
            raise

    def exception_handler(self, exc_info, args_obj, args_dict, extra_args):
        """Handler for doing things like bugsnag"""

    def setup_logging(self, args_obj, log=None, only_message=False):
        """Setup the handler for the logs and call setup_other_logging"""
        level = [logging.INFO, logging.DEBUG][args_obj.verbose or args_obj.debug]
        if args_obj.silent:
            level = logging.ERROR

        handler = setup_logging(
            log=log,
            level=level,
            program=args_obj.logging_program,
            syslog_address=args_obj.syslog_address,
            udp_address=args_obj.udp_logging_address,
            tcp_address=args_obj.tcp_logging_address,
            only_message=only_message,
            logging_handler_file=self.logging_handler_file,
            json_to_console=args_obj.json_console_logs,
        )

        self.setup_other_logging(args_obj, args_obj.verbose, args_obj.silent, args_obj.debug)
        return handler

    def setup_logging_theme(self, handler, colors="light"):
        """
        Setup a logging theme, the two options for colors is light and dark

        Note that nothing calls this method by default
        """
        return setup_logging_theme(handler, colors=colors)

    def make_cli_parser(self):
        """Return a CliParser instance"""
        properties = {"specify_other_args": self.specify_other_args}
        kls = type("CliParser", (self.CliParserKls,), properties)
        return kls(
            self.cli_description, self.cli_positional_replacements, self.cli_environment_defaults
        )


########################
###   CliParser
########################


class CliParser(object):
    """Knows what argv looks like"""

    def __init__(self, description, positional_replacements=None, environment_defaults=None):
        self.description = description
        self.positional_replacements = positional_replacements
        if self.positional_replacements is None:
            self.positional_replacements = []

        self.environment_defaults = environment_defaults
        if self.environment_defaults is None:
            self.environment_defaults = {}

    def specify_other_args(self, parser, defaults):
        """Hook to specify more arguments"""

    def interpret_args(self, argv, categories=None):
        """
        Parse argv and return (args_obj, args_dict, extra)

        Where args_obj is the object return by argparse
        extra is all the arguments after a ``--``
        and args_dict is a dictionary representation of the args_obj object
        """
        if categories is None:
            categories = []
        args_obj, extra = self.parse_args(argv)

        args_dict = {}
        for category in categories:
            args_dict[category] = {}
        for key, val in sorted(vars(args_obj).items()):
            found = False
            for category in categories:
                if key.startswith("{0}_".format(category)):
                    args_dict[category][key[(len(category) + 1) :]] = val
                    found = True
                    break

            if not found:
                args_dict[key] = val

        return args_obj, args_dict, extra

    def parse_args(self, argv=None):
        """
        Build up an ArgumentParser and parse our argv!

        Also complain if any ``--argument`` is both specified explicitly and
        as a positional
        """
        if argv is None:
            argv = sys.argv[1:]
        args, other_args, defaults = self.split_args(argv)
        parser = self.make_parser(defaults)
        parsed = parser.parse_args(args)
        self.check_args(argv, defaults, self.positional_replacements)
        return parsed, other_args

    def check_args(self, argv, defaults, positional_replacements):
        """Check that we haven't specified an arg as positional and a ``--flag``"""
        num_positionals = 0
        args = []
        for thing in argv:
            if thing == "--":
                break
            if thing.startswith("-"):
                args.append(thing)
            elif not args:
                num_positionals += 1

        for index, replacement in enumerate(positional_replacements):
            if type(replacement) is tuple:
                replacement, _ = replacement
            if (
                index < num_positionals
                and "default" in defaults.get(replacement, {})
                and replacement in args
            ):
                raise BadOption(
                    "Please don't specify an option as a positional argument and as a --flag",
                    argument=replacement,
                    position=index + 1,
                )

    def split_args(self, argv):
        """
        Split up argv into args, other_args and defaults

        Other args is anything after a ``--`` and args is everything before a
        ``--``
        """
        if argv is None:
            argv = sys.argv[1:]

        args = []
        argv = list(argv)
        extras = None

        while argv:
            nxt = argv.pop(0)
            if extras is not None:
                extras.append(nxt)
            elif nxt == "--":
                extras = []
            else:
                args.append(nxt)

        other_args = ""
        if extras:
            other_args = " ".join(extras)

        defaults = self.make_defaults(args, self.positional_replacements, self.environment_defaults)
        return args, other_args, defaults

    def make_defaults(self, argv, positional_replacements, environment_defaults):
        """
        Make and return a dictionary of ``{--flag: {"default": value}}``

        This method will also remove the positional arguments from argv
        that map to positional_replacements.

        Defaults are populated from mapping environment_defaults to ``--arguments``
        and mapping positional_replacements to ``--arguments``

        So if positional_replacements is ``[--stack]`` and argv is
        ``["blah", "--stuff", 1]`` defaults will equal
        ``{"--stack": {"default": "blah"}}``

        If environment_defaults is ``{"CONFIG_LOCATION": "--config"}``
        and os.environ["CONFIG_LOCATION"] = "/a/path/to/somewhere.yml"
        then defaults will equal ``{"--config": {"default": "/a/path/to/somewhere.yml"}}``

        Positional arguments will override environment defaults.
        """
        defaults = {}

        class Ignore(object):
            pass

        for env_name, replacement in environment_defaults.items():
            default = Ignore
            if type(replacement) is tuple:
                replacement, default = replacement

            if env_name in os.environ:
                defaults[replacement] = {"default": os.environ[env_name]}
            else:
                if default is Ignore:
                    defaults[replacement] = {}
                else:
                    defaults[replacement] = {"default": default}

        for replacement in positional_replacements:
            if type(replacement) is tuple:
                replacement, _ = replacement
            if argv and not argv[0].startswith("-"):
                defaults[replacement] = {"default": argv[0]}
                argv.pop(0)
            else:
                break

        for replacement in positional_replacements:
            default = Ignore
            if type(replacement) is tuple:
                replacement, default = replacement
            if replacement not in defaults:
                if default is Ignore:
                    defaults[replacement] = {}
                else:
                    defaults[replacement] = {"default": default}

        return defaults

    def make_parser(self, defaults):
        """Create an argparse ArgumentParser with some default flags for logging"""
        parser = argparse.ArgumentParser(description=self.description)

        logging = parser.add_mutually_exclusive_group()
        logging.add_argument("--verbose", help="Enable debug logging", action="store_true")

        if "default" in defaults.get("--silent", {}):
            kwargs = defaults["--silent"]
        else:
            kwargs = {"action": "store_true"}
        logging.add_argument("--silent", help="Only log errors", **kwargs)

        logging.add_argument("--debug", help="Debug logs", action="store_true")

        logging.add_argument(
            "--logging-program", help="The program name to use when not logging to the console"
        )

        parser.add_argument(
            "--tcp-logging-address",
            help="The address to use for giving log messages to tcp (i.e. localhost:9001)",
            default="",
        )

        parser.add_argument(
            "--udp-logging-address",
            help="The address to use for giving log messages to udp (i.e. localhost:9001)",
            default="",
        )

        parser.add_argument(
            "--syslog-address", help="The address to use for syslog (i.e. /dev/log)", default=""
        )

        parser.add_argument(
            "--json-console-logs",
            help="If we haven't set other logging arguments, this will mean we log json lines to the console",
            action="store_true",
        )

        parser.add_argument("--version", help="Print out the version!", action="store_true")

        self.specify_other_args(parser, defaults)
        return parser
