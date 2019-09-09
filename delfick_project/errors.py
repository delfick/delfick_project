"""
delfick_project provides a custom error class for making working with
exceptions a little nicer.

Usage looks like:

.. code-block:: python
    
    from delfick_project.errors import DelfickError

    class MyError(DelfickError):
        desc = "something went wrong"

    raise MyError("Computer says no", arg1=True, arg2=3)

DelfickError instances have the following properties:

* Instantiation takes a message and arbitrary keyword arguments. if one of the
  arguments is ``_errors`` then this will be treated specially when presenting
  the error as a string, and will be available on the instance as ``error.errors``

  All other keyword arguments are available under ``error.kwargs``

* ``__str__`` takes into account desc on the class, the message given to the
  instance,  any _errors on the instance and the rest of the keyword arguments.

* ``error.as_dict()`` returns the error as a dictionary. a "message" key will
  combine desc on the class and the message given to the instance. "errors" will
  be a list of the _errors list as dictionaries (or string for errors that have
  no ``as_dict`` method. And the rest of ``error.kwargs`` in the dictionary.

* Instances can be used as keys in a dictionary. It matches on a
  tuple of ``(error_kls, messages, kwargs_as_tuple, errors_as_tuple)``

* Instances can be used in an equality check based off the same
  information used to make it hashable

* Instances are sortable

This module also provides:

.. autoclass:: ProgrammerError

.. autoclass:: UserQuit

.. autoclass:: DelfickErrorTestMixin
"""
from contextlib import contextmanager
from functools import total_ordering
from unittest.util import safe_repr
import traceback
import sys
import re


@total_ordering
class DelfickError(Exception):
    """Helpful class for creating custom exceptions"""

    desc = ""

    def __init__(self, message="", **kwargs):
        self.kwargs = kwargs
        self.errors = kwargs.get("_errors", [])
        if "_errors" in kwargs:
            del kwargs["_errors"]
        self.message = message
        super(DelfickError, self).__init__(message)

    def __str__(self):
        message = self.oneline()
        if self.errors:
            message = "{0}\nerrors:\n=======\n\n\t{1}".format(
                message,
                "\n\t".join(
                    "{0}\n-------".format("\n\t".join(str(error).split("\n")))
                    for error in self.errors
                ),
            )
        return message

    def as_dict(self):
        desc = self.desc
        message = self.message
        if desc:
            if message:
                message = ". {0}".format(message)
            desc = "{0}{1}".format(desc, message)
        else:
            if message:
                desc = message
            else:
                desc = None

        res = {}
        if desc is not None:
            res["message"] = desc
        res.update(dict((k, self.formatted_val(k, v)) for k, v in self.kwargs.items()))

        if self.errors:
            res["errors"] = [
                repr(e) if not hasattr(e, "as_dict") else e.as_dict() for e in self.errors
            ]
        return res

    def __unicode__(self):
        return str(self).decode("utf-8")

    def __repr__(self):
        return "{0}({1}, {2}, _errors={3})".format(
            self.__class__.__name__,
            self.message,
            ", ".join("{0}={1}".format(k, v) for k, v in self.kwargs.items()),
            self.errors,
        )

    def __hash__(self):
        return hash(self.as_tuple(for_hash=True))

    def oneline(self):
        """Get back the error as a oneliner"""
        desc = self.desc
        message = self.message

        info = [
            "{0}={1}".format(k, self.formatted_val(k, v)) for k, v in sorted(self.kwargs.items())
        ]
        info = "\t".join(info)
        if info and (message or desc):
            info = "\t{0}".format(info)

        if desc:
            if message:
                message = ". {0}".format(message)
            return '"{0}{1}"{2}'.format(desc, message, info)
        else:
            if message:
                return '"{0}"{1}'.format(message, info)
            else:
                return "{0}".format(info)

    def formatted_val(self, key, val):
        """Format a value for display in error message"""
        if not hasattr(val, "delfick_error_format"):
            return val
        else:
            try:
                return val.delfick_error_format(key)
            except Exception as error:
                return "<|Failed to format val for exception: val={0}, error={1}|>".format(
                    val, error
                )

    def __eq__(self, error):
        """Say whether this error is like the other error"""
        if error.__class__ != self.__class__ or error.message != self.message:
            return False

        self_kwargs = self.as_tuple(formatted=True)[2]
        error_kwargs = error.as_tuple(formatted=True)[2]
        return error_kwargs == self_kwargs and sorted(self.errors) == sorted(error.errors)

    def __lt__(self, error):
        return self.as_tuple(formatted=True) < error.as_tuple(formatted=True)

    def as_tuple(self, for_hash=False, formatted=False):
        kwarg_items = sorted(self.kwargs.items())
        if formatted:
            final = []
            for key, val in kwarg_items:
                if hasattr(val, "delfick_error_format"):
                    final.append((key, val.delfick_error_format(key)))
                else:
                    final.append((key, val))
            kwarg_items = sorted(final)
        if for_hash:
            kwarg_items = [(key, str(val)) for key, val in kwarg_items]
        return (self.__class__.__name__, self.message, tuple(kwarg_items), tuple(self.errors))


class ProgrammerError(Exception):
    """
    A non DelfickError exception for when the programmer should have prevented
    something happening
    """


class Empty:
    def __repr__(self):
        return "<EMPTY>"


class UserQuit(DelfickError):
    """Raise this if the user quit the application"""

    desc = "User Quit"


class DelfickErrorTestMixin:
    """
    A mixin for use with ``unittest.TestCase`` that provides the ability to
    test for DelfickError exceptions.

    .. code-block:: python

        from delfick_project.errors import DelfickErrorTestMixin

        from unittest import TestCase

        class TestThings(TestCase, DelfickErrorTestMixin):
            def test_something(self):
                error1 = DelfickError("something bad happend")
                with self.fuzzyAssertRaisesError(MyError, "nope", arg1=2, _errors=[error1]):
                    raise MyError("nope", arg1=2, arg2=3, _errors=[error1])

    .. automethod:: fuzzyAssertRaisesError
    """

    @contextmanager
    def fuzzyAssertRaisesError(self, expected_kls, expected_msg_regex=Empty, **values):
        """
        Assert that something raises a particular type of error.

        The error raised must be a subclass of the expected_kls
        Have a message that matches the specified regex.

        And have atleast the values specified in it's kwargs.
        """
        try:
            yield
        except Exception as error:
            original_exc_info = sys.exc_info()
            try:
                assert issubclass(error.__class__, expected_kls), "Expected {0}, got {1}".format(
                    expected_kls, error.__class__
                )

                if not issubclass(error.__class__, DelfickError) and not getattr(
                    error, "_fake_delfick_error", False
                ):
                    # For normal exceptions we just regex against the string of the whole exception
                    if expected_msg_regex is not Empty:
                        self.assertMatchingRegex(str(error), expected_msg_regex)
                else:
                    # For special DelfickError exceptions, we compare against error.message, error.kwargs and error._errors
                    if expected_msg_regex is not Empty:
                        self.assertMatchingRegex(error.message, expected_msg_regex)

                    errors = values.get("_errors")
                    if "_errors" in values:
                        del values["_errors"]

                    self.assertDictContains(values, error.kwargs)
                    if errors:
                        self.assertEqual(sorted(error.errors), sorted(errors))
            except AssertionError:
                exc_info = sys.exc_info()
                try:
                    print("!" * 20)
                    print(
                        "".join(
                            ["Original Traceback\n"] + traceback.format_tb(original_exc_info[2])
                        ).strip()
                    )
                    print(error)
                    print()
                    msg = "Expected: {0}".format(expected_kls)
                    if expected_msg_regex is not Empty:
                        msg = "{0}: {1}".format(msg, expected_msg_regex)
                    if values:
                        msg = "{0}: {1}".format(msg, values)
                    print(msg)
                    print("!" * 20)
                finally:
                    exc_info[1].__traceback__ = exc_info[2]
                    raise exc_info[1]
        else:
            assert (
                False
            ), "Expected an exception to be raised\n\texpected_kls: {0}\n\texpected_msg_regex: {1}\n\thave_atleast: {2}".format(
                expected_kls, expected_msg_regex, values
            )

    def assertDictContains(self, expected, actual, msg=None):
        """Checks whether actual is a superset of expected."""
        missing = []
        mismatched = []
        for key, value in expected.items():
            if key not in actual:
                missing.append(safe_repr(key))
            elif value != actual[key]:
                nxt = "{{{0}: expected={1}, got={2}}}".format(
                    safe_repr(key), safe_repr(value), safe_repr(actual[key])
                )
                mismatched.append(nxt)

        if not (missing or mismatched):
            return

        error = []
        if missing:
            error.append("Missing: {0}".format(", ".join(sorted(missing))))

        if mismatched:
            error.append("Mismatched: {0}".format(", ".join(sorted(mismatched))))

        if hasattr(self, "_formatMessage"):
            self.fail(self._formatMessage(msg, "; ".join(error)))
        else:
            self.fail(msg or "; ".join(error))

    def assertMatchingRegex(self, text, expected_regex, msg=None):
        """Fail the test unless the text matches the regular expression."""
        if isinstance(expected_regex, (str, bytes)):
            assert expected_regex, "expected_regex must not be empty."
            expected_regex = re.compile(expected_regex)
        if not expected_regex.search(text):
            msg = msg or "Regex didn't match"
            msg = "%s: %r not found in %r" % (msg, expected_regex.pattern, text)
            raise self.failureException(msg)
