# coding: spec

from delfick_project.app import CliParser, Ignore, BadOption

from contextlib import contextmanager
from unittest import mock, TestCase
from itertools import combinations
import sys
import re
import os

describe TestCase, "CliParser":
    @contextmanager
    def swapped_env(self, **swapped):
        originals = {}
        try:
            for name, val in swapped.items():
                originals[name] = os.environ.get(name, Ignore)
                os.environ[name] = val
            yield
        finally:
            for name in swapped:
                original = originals[name]
                if original is Ignore and name in os.environ:
                    del os.environ[name]
                elif original is not Ignore:
                    os.environ[name] = original

    it "takes in description, positional_replacements and environment_defaults":
        description = mock.Mock(name="description")
        environment_defaults = mock.Mock(name="environment_defaults")
        positional_replacements = mock.Mock(name="positional_replacements")

        parser = CliParser(description, environment_defaults=environment_defaults, positional_replacements=positional_replacements)
        self.assertIs(parser.description, description)
        self.assertIs(parser.environment_defaults, environment_defaults)
        self.assertIs(parser.positional_replacements, positional_replacements)

    it "defaults positional_replacements to an empty array":
        self.assertEqual(CliParser(None).positional_replacements, [])

    it "defaults environment_defaults to an empty dictionary":
        self.assertEqual(CliParser(None).environment_defaults, {})

    describe "parse_args":
        it "splits, makes, parses and checks the args":
            argv = mock.Mock(name="argv")
            args_obj = mock.Mock(name="args_obj")
            other_args = mock.Mock(name="other_args")
            defaults = mock.Mock(name="defaults")
            positional_replacements = mock.Mock(name="positional_replacements")

            parser = mock.Mock(name='parser')
            parsed = mock.Mock(name='parsed')
            parser.parse_args.return_value = parsed

            split_args = mock.Mock(name="split_args", return_value=(args_obj, other_args, defaults))
            make_parser = mock.Mock(name="make_parser", return_value=parser)
            check_args = mock.Mock(name="check_args")

            cli_parser = CliParser("", positional_replacements)
            with mock.patch.multiple(cli_parser, split_args=split_args, make_parser=make_parser, check_args=check_args):
                self.assertEqual(cli_parser.parse_args(argv), (parsed, other_args))

            make_parser.assert_called_once_with(defaults)
            parser.parse_args.assert_called_once_with(args_obj)
            check_args.assert_called_once_with(argv, defaults, positional_replacements)

        it "works":
            class Parser(CliParser):
                def specify_other_args(slf, parser, defaults):
                    parser.add_argument("--task"
                        , help = "specify the task"
                        , **defaults["--task"]
                        )

                    parser.add_argument("--blah"
                        , help = "I don't know"
                        , **defaults["--blah"]
                        )

                    parser.add_argument("--meh"
                        , help = "I don't know"
                        )

            parser = Parser("", [("--task", "list_tasks"), "--blah"], {})
            parsed, other_args = parser.parse_args(['whatever', 'tree', '--meh', 'bus', '--', '--blah', 'fire'])

            self.assertEqual(other_args, '--blah fire')
            self.assertEqual(parsed.task, "whatever")
            self.assertEqual(parsed.blah, "tree")
            self.assertEqual(parsed.meh, "bus")

        it "works in the error case":
            class Parser(CliParser):
                def specify_other_args(slf, parser, defaults):
                    parser.add_argument("--task"
                        , help = "specify the task"
                        , **defaults["--task"]
                        )

            parser = Parser("", ["--task"], {})
            with self.fuzzyAssertRaisesError(BadOption, "Please don't specify an option as a positional argument and as a --flag", argument="--task", position=1):
                parsed, other_args = parser.parse_args(['whatever', '--task', 'whatever', '--', '--task', 'fire'])

    describe "check_args":
        it "complains if it finds something both has a default and is in args and positional_replacements":
            positional_replacements = ['--task', '--env']
            defaults = {'--task': {}, "--env": {"default": "prod"}}
            parser = CliParser("")

            parser.check_args([], defaults, positional_replacements)
            assert True, "That definitely should not have failed"

            with self.fuzzyAssertRaisesError(BadOption, "Please don't specify an option as a positional argument and as a --flag", argument="--env", position=2):
                parser.check_args(['list_tasks', 'dev', '--env', 'staging'], defaults, positional_replacements)

    describe "interpret_args":
        it "can categorize based on categories and names of args":
            class Parser(CliParser):
                def specify_other_args(slf, parser, defaults):
                    parser.add_argument("--one"
                        , dest = 'my_app_one'
                        )

                    parser.add_argument('--two'
                        , dest = 'my_app_two'
                        )

                    parser.add_argument('--other')

            parser = Parser("")
            args_obj, args_dict, extra = parser.interpret_args(["--one", "1", "--two", "2", "--other", "3", "--logging-program", "my-app", "--syslog-address", "/dev/log"], ["my_app"])

            self.assertEqual(extra, "")

            self.assertEqual(args_obj.my_app_one, "1")
            self.assertEqual(args_obj.my_app_two, "2")
            self.assertEqual(args_obj.other, "3")
            self.assertEqual(args_obj.logging_program, "my-app")

            self.assertEqual(args_dict
                , {
                    "my_app":
                    { "one": "1", "two": "2" }
                  , "other": "3"
                  , "silent": False
                  , "debug": False
                  , "verbose": False
                  , "version": False
                  , "logging_program": "my-app"
                  , "syslog_address": "/dev/log"
                  , "json_console_logs": False
                  , "tcp_logging_address": ""
                  , "udp_logging_address": ""
                  }
                )

        it "Doesn't complain about flagged values in positional placement":
            class Parser(CliParser):
                def specify_other_args(slf, parser, defaults):
                    parser.add_argument("--one"
                        , **defaults["--one"]
                        )
                    parser.add_argument("--two"
                        , **defaults["--two"]
                        )
                    parser.add_argument("--three"
                        , **defaults["--three"]
                        )

            parser = Parser("", ["--one", "--two", ("--three", 'dflt')], {})
            parsed, args_dict, extra = parser.interpret_args(['whatever', '--three', 'whatever2', '--two', 'stuff'])
            self.assertEqual(parsed.one, "whatever")
            self.assertEqual(parsed.two, "stuff")
            self.assertEqual(parsed.three, "whatever2")

        it "does complain about flagged values combined with positional placement":
            class Parser(CliParser):
                def specify_other_args(slf, parser, defaults):
                    parser.add_argument("--one"
                        , **defaults["--one"]
                        )
                    parser.add_argument("--two"
                        , **defaults["--two"]
                        )
                    parser.add_argument("--three"
                        , **defaults["--three"]
                        )

            parser = Parser("", ["--one", "--two", ("--three", 'dflt')], {})
            with self.fuzzyAssertRaisesError(BadOption, "Please don't specify an option as a positional argument and as a --flag", argument="--two", position=2):
                parser.interpret_args(['whatever', 'trees', 'whatever2', '--two', 'stuff'])

    describe "make_defaults":
        it "has no defaults if there are no positional_replacements or environment_defaults":
            parser = CliParser("")
            defaults = parser.make_defaults([], [], {})
            self.assertEqual(defaults, {})

            argv = ['one', 'two', '--three']
            defaults = parser.make_defaults(argv, [], {})
            self.assertEqual(defaults, {})
            self.assertEqual(argv, ['one', 'two', '--three'])

        it "maps argv positionals to positional_replacements and takes those from argv":
            argv = ['one', 'two', 'three']
            positional_replacements = ['--task', '--env', '--stack']
            parser = CliParser("")
            defaults = parser.make_defaults(argv, positional_replacements, {})

            self.assertEqual(argv, [])
            self.assertEqual(defaults, {"--task": {"default": "one"}, "--env": {"default": "two"}, "--stack": {"default": "three"}})

        it "ignores positional_replacements after a -flag":
            argv = ['one', 'two', '-three']
            positional_replacements = ['--task', '--env', '--stack']
            parser = CliParser("")
            defaults = parser.make_defaults(argv, positional_replacements, {})

            self.assertEqual(argv, ['-three'])
            self.assertEqual(defaults, {"--task": {"default": "one"}, "--env": {"default": "two"}, "--stack": {}})

        it "finds environment variables from environment_defaults as defaults":
            argv = []
            environment_defaults = {"CONFIG_LOCATION": '--config'}
            parser = CliParser("")

            somewhere = "/some/nice/config.yml"
            with self.swapped_env(CONFIG_LOCATION=somewhere):
                defaults = parser.make_defaults(argv, [], environment_defaults)

                self.assertEqual(argv, [])
                self.assertEqual(defaults, {"--config": {"default": somewhere}})

        it "uses default from environment if flag in positional_replacements":
            argv = []
            environment_defaults = {"CONFIG_LOCATION": '--config'}
            positional_replacements = ["--config"]
            parser = CliParser("")

            somewhere = "/some/nice/config.yml"
            with self.swapped_env(CONFIG_LOCATION=somewhere):
                defaults = parser.make_defaults(argv, positional_replacements, environment_defaults)

                self.assertEqual(argv, [])
                self.assertEqual(defaults, {"--config": {"default": somewhere}})

        it "overrides default from environment_defaults with value from argv if in positional_replacements":
            argv = ["a/better/place.yml"]
            environment_defaults = {"CONFIG_LOCATION": '--config'}
            positional_replacements = ["--config"]
            parser = CliParser("")

            somewhere = "/some/nice/config.yml"
            with self.swapped_env(CONFIG_LOCATION=somewhere):
                defaults = parser.make_defaults(argv, positional_replacements, environment_defaults)

                self.assertEqual(argv, [])
                self.assertEqual(defaults, {"--config": {"default": 'a/better/place.yml'}})

        it "environment_defaults overrides positional_replacements default":
            argv = []
            environment_defaults = {"CONFIG_LOCATION": '--config'}
            positional_replacements = [("--config", "a/nicer/place.yml")]
            parser = CliParser("")

            somewhere = "/some/nice/config.yml"
            with self.swapped_env(CONFIG_LOCATION=somewhere):
                defaults = parser.make_defaults(argv, positional_replacements, environment_defaults)

                self.assertEqual(argv, [])
                self.assertEqual(defaults, {"--config": {"default": somewhere}})

        it "environment_defaults default value overrides positional_replacements default":
            argv = []
            environment_defaults = {"CONFIG_LOCATION": ('--config', 'the/best/place.yml')}
            positional_replacements = [("--config", "a/nicer/place.yml")]
            parser = CliParser("")

            somewhere = "/some/nice/config.yml"
            defaults = parser.make_defaults(argv, positional_replacements, environment_defaults)

            self.assertEqual(argv, [])
            self.assertEqual(defaults, {"--config": {"default": 'the/best/place.yml'}})

        it "can have defaults for positional_replacements":
            argv = []
            positional_replacements = [("--task", "list_tasks")]
            parser = CliParser("")

            defaults = parser.make_defaults(argv, positional_replacements, {})

            self.assertEqual(argv, [])
            self.assertEqual(defaults, {"--task": {"default": "list_tasks"}})

        it "can have defaults for environment_defaults":
            argv = []
            environment_defaults = {'SOMETHING': ("--something", "something")}
            parser = CliParser("")

            defaults = parser.make_defaults(argv, [], environment_defaults)

            self.assertEqual(argv, [])
            self.assertEqual(defaults, {"--something": {"default": "something"}})

    describe "split_args":
        it "returns args before and after -- and calls make_defaults":
            dflts = mock.Mock(name="dflts")
            make_defaults = mock.Mock(name="make_defaults", return_value=dflts)

            description = mock.Mock(name="description")
            environment_defaults = mock.Mock(name="environment_defaults")
            positional_replacements = mock.Mock(name="positional_replacements")

            parser = CliParser(description, positional_replacements, environment_defaults)
            with mock.patch.object(parser, "make_defaults", make_defaults):
                args, other_args, defaults = parser.split_args(['a', 'b', 'c', '--', 'd', 'e', 'f'])

            self.assertEqual(args, ['a', 'b', 'c'])
            self.assertEqual(other_args, 'd e f')
            self.assertIs(defaults, dflts)
            make_defaults.assert_called_once_with(['a', 'b', 'c'], positional_replacements, environment_defaults)

        it "returns other_args as empty if there is no --":
            args, other_args, defaults = CliParser("").split_args(['a', 'b', 'c'])
            self.assertEqual(args, ['a', 'b', 'c'])
            self.assertEqual(other_args, '')
            self.assertEqual(defaults, {})

        it "sets args as an empty list if args is just from --":
            args, other_args, defaults = CliParser("").split_args(['--', 'a', 'b', 'c'])
            self.assertEqual(args, [])
            self.assertEqual(other_args, 'a b c')
            self.assertEqual(defaults, {})

        it "works":
            argv = ['dev', '--blah', '1', '--', 'and', 'stuff']
            args, other_args, defaults = CliParser("", ['--env', ('--task', 'list_tasks')], {"CONFIG_LOCATION": ("--config", 'somewhere')}).split_args(argv)

            self.assertEqual(args, ['--blah', '1'])
            self.assertEqual(other_args, 'and stuff')
            self.assertEqual(defaults, {'--env': {"default": "dev"}, "--task": {"default": "list_tasks"}, "--config": {"default": "somewhere"}})

    describe "make_parser":
        it "calls specify_other_args with the parser":
            parser = mock.Mock(name="parser")
            defaults = {"--silent": {"default": False}}
            description = mock.Mock(name="description")
            FakeArgumentParser = mock.Mock(name="ArgumentParser", return_value=parser)

            called = []
            class Parser(CliParser):
                def specify_other_args(slf, parser, defaults):
                    called.append((parser, defaults))

            with mock.patch("argparse.ArgumentParser", FakeArgumentParser):
                self.assertIs(Parser(description).make_parser(defaults), parser)

            self.assertEqual(called, [(parser, defaults)])
            FakeArgumentParser.assert_called_once_with(description=description)

        it "specifies verbose, silent and debug":
            parser = CliParser("").make_parser({})

            args_obj = parser.parse_args([])
            self.assertIs(args_obj.verbose, False)
            self.assertIs(args_obj.silent, False)
            self.assertIs(args_obj.debug, False)

            args_obj = parser.parse_args(["--verbose"])
            self.assertIs(args_obj.verbose, True)
            self.assertIs(args_obj.silent, False)
            self.assertIs(args_obj.debug, False)

            args_obj = parser.parse_args(["--silent"])
            self.assertIs(args_obj.verbose, False)
            self.assertIs(args_obj.silent, True)
            self.assertIs(args_obj.debug, False)

            args_obj = parser.parse_args(["--debug"])
            self.assertIs(args_obj.verbose, False)
            self.assertIs(args_obj.silent, False)
            self.assertIs(args_obj.debug, True)

        it "complains if silent, verbose and debug are specified at the same time":
            called = []
            parser = CliParser("").make_parser({})
            print_usage = mock.Mock(name="print_usage")

            def print_message(message, fle):
                called.append(message)
                self.assertIs(fle, sys.stderr)

            print_message = mock.Mock(name='print_message', side_effect=print_message)
            with mock.patch.multiple(parser, print_usage=print_usage, _print_message=print_message):
                for combination in list(combinations(["--verbose", "--silent", "--debug"], 2)) + [["--verbose", "--silent", "--debug"]]:
                    try:
                        parser.parse_args(combination)
                        assert False, "That should have failed"
                    except SystemExit as error:
                        self.assertEqual(error.code, 2)

            self.assertEqual(len(called), 4)
            regex = re.compile("nosetests: error: argument (--silent|--verbose|--debug): not allowed with argument (--silent|--verbose|--debug)")
            for message in called:
                match = regex.match(message)
                assert match, "Message {0} did not match regex {1}".format(message, regex.pattern)
                groups = set(match.groups())
                self.assertEqual(len(groups), 2, message)