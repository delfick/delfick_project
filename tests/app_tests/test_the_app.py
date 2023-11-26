# coding: spec

import datetime
import io
import logging
import re
from textwrap import dedent
from unittest import mock

import pytest

from delfick_project.app import App, CliParser
from delfick_project.errors import DelfickError
from delfick_project.errors_pytest import assertRaises


@pytest.fixture(autouse=True)
def reset_log_handlers():
    root = logging.getLogger(None)
    oldhandlers = list(root.handlers)
    try:
        yield
    finally:
        root.handlers = oldhandlers


describe "App":
    describe "main":
        it "Instantiates the class and calls the mainline":
            called = []
            argv = mock.Mock(name="argv")

            class MyApp(App):
                def mainline(s, argv=None):
                    called.append(argv)

            MyApp.main(argv)
            assert called == [argv]

    describe "mainline":
        it "catches DelfickError errors and prints them nicely":
            fle = io.StringIO()

            class MyApp(App):
                def execute(slf, args_obj, args_dict, extra_args, handler):
                    raise DelfickError(
                        "Well this should work",
                        blah=1,
                        _errors=[
                            DelfickError("SubError", meh=2),
                            DelfickError("SubError2", stuff=3),
                        ],
                    )

            try:
                MyApp().mainline([], print_errors_to=fle)
                assert False, "This should have failed"
            except SystemExit as error:
                assert error.code == 1

            fle.flush()
            fle.seek(0)
            assert fle.read() == (
                dedent(
                    """
                !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                Something went wrong! -- DelfickError
                \t"Well this should work"\tblah=1
                errors:
                =======

                \t"SubError"\tmeh=2
                -------
                \t"SubError2"\tstuff=3
                -------
            """
                )
            )

        it "Converts KeyboardInterrupt into a UserQuit":
            fle = io.StringIO()

            class MyApp(App):
                def execute(slf, args_obj, args_dict, extra_args, handler):
                    raise KeyboardInterrupt()

            try:
                MyApp().mainline([], print_errors_to=fle)
                assert False, "This should have failed"
            except SystemExit as error:
                assert error.code == 1

            fle.flush()
            fle.seek(0)
            assert fle.read() == (
                dedent(
                    """
                !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                Something went wrong! -- UserQuit
                \t"User Quit"
            """
                )
            )

        it "Does not catch non DelfickError exceptions":
            error = ValueError("hi")

            class MyApp(App):
                def execute(slf, args_obj, args_dict, extra_args, handler):
                    raise error

            with assertRaises(ValueError):
                MyApp().mainline([])

        it "raises DelfickError exceptions if we have --debug":

            class MyApp(App):
                def execute(slf, args_obj, args_dict, extra_args, handler):
                    raise DelfickError("hi there", meh=2)

            with assertRaises(DelfickError, "hi there", meh=2):
                MyApp().mainline(["--debug"])

        it "raises the KeyboardInterrupt if we have --debug":

            class MyApp(App):
                def execute(slf, args_obj, args_dict, extra_args, handler):
                    raise KeyboardInterrupt()

            with assertRaises(KeyboardInterrupt):
                MyApp().mainline(["--debug"])

        it "parse args, sets up logging, and calls execute":
            called = []

            cli_parser = mock.Mock(name="cli_parser")
            argv = mock.Mock(name="argv")
            cli_categories = mock.Mock(name="cli_categories")
            args_obj = mock.Mock(name="args_obj", version=False)
            extra_args = mock.Mock(name="extra_args")
            args_dict = mock.Mock(name="args_dict")
            handler = mock.Mock(name="handler")

            cli_parser.interpret_args = mock.Mock(name="interpret_args")

            def interpret_args(*a):
                called.append(1)
                return (args_obj, args_dict, extra_args)

            cli_parser.interpret_args.side_effect = interpret_args

            setup_logging = mock.Mock(name="setup_logging")

            def stp_lging(*a, **kw):
                called.append(2)
                return handler

            setup_logging.side_effect = stp_lging

            execute = mock.Mock(name="execute")
            execute.side_effect = lambda *args: called.append(4)

            class MyApp(App):
                def make_cli_parser(slf):
                    return cli_parser

            app = MyApp()

            with mock.patch.multiple(
                app, execute=execute, setup_logging=setup_logging, cli_categories=cli_categories
            ):
                app.mainline(argv)

            cli_parser.interpret_args.assert_called_once_with(argv, cli_categories)
            setup_logging.assert_called_once_with(args_obj)
            execute.assert_called_once_with(args_obj, args_dict, extra_args, handler)

    describe "setup_logging":
        it "works":
            fle = io.StringIO()

            class MyApp(App):
                logging_handler_file = fle

            root = logging.getLogger(None)

            app = MyApp()
            args_obj, _, _ = app.make_cli_parser().interpret_args([])
            logging_handler = app.setup_logging(args_obj)

            log = logging.getLogger("blah")

            log.info("hello there")
            log.error("hmmm")
            log.debug("not captured")
            log.warning("yeap")

            root.removeHandler(logging_handler)
            args_obj, _, _ = app.make_cli_parser().interpret_args(["--verbose"])
            logging_handler = app.setup_logging(args_obj)
            log.debug("this one is captured")

            root.removeHandler(logging_handler)
            args_obj, _, _ = app.make_cli_parser().interpret_args(["--silent"])
            logging_handler = app.setup_logging(args_obj)
            log.debug("not captured")
            log.warning("not captured")
            log.info("not captured")
            log.error("also captured")

            fle.flush()
            fle.seek(0)
            logs = fle.readlines()
            now = datetime.datetime.now()
            date = now.strftime("%Y-%m-%d [^ ]+")
            expect = [
                re.compile("{0} INFO    blah            hello there".format(date)),
                re.compile("{0} ERROR   blah            hmmm".format(date)),
                re.compile("{0} WARNING blah            yeap".format(date)),
                re.compile("{0} DEBUG   blah            this one is captured".format(date)),
                re.compile("{0} ERROR   blah            also captured".format(date)),
            ]

            assert len(expect) == len(logs), logs
            for index, line in enumerate(expect):
                assert line.match(logs[index].strip()), "Expected '{0}' to match '{1}'".format(
                    logs[index].strip().replace("\t", "\\t").replace(" ", "."),
                    line.pattern.replace("\t", "\\t").replace(" ", "."),
                )

    describe "make_cli_parser":
        it "creates a CliParser with specify_other_args grafted onto it and initialized with self.cli_ attributes":
            called = []
            parser = mock.Mock(name="parser")
            defaults = mock.Mock(name="defaults")

            description = mock.Mock(name="descrption")
            environment_defaults = mock.Mock(name="environment_defaults")
            positional_replacements = mock.Mock(name="positional_replacements")

            class MyApp(App):
                cli_description = description
                cli_environment_defaults = environment_defaults
                cli_positional_replacements = positional_replacements

                def specify_other_args(slf, p, d):
                    called.append((slf, p, d))

            app = MyApp()
            cli_parser = app.make_cli_parser()
            assert isinstance(cli_parser, CliParser)
            assert cli_parser.description is description
            assert cli_parser.environment_defaults is environment_defaults
            assert cli_parser.positional_replacements is positional_replacements

            assert called == []
            cli_parser.specify_other_args(parser, defaults)
            assert called == [(app, parser, defaults)]
