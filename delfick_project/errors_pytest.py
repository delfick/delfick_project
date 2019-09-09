"""
.. autofunction:: assertRaises
"""
from delfick_project.errors import DelfickError

from textwrap import dedent
import traceback
import sys
import re


class RegexCompare:
    def __init__(self, regex):
        self.r = re.compile(regex)

    def __eq__(self, other):
        return self.r.search(other) is not None

    def __repr__(self):
        return "<Regex '{0}'>".format(self.r.pattern)


class Empty:
    def __repr__(self):
        return "<EMPTY>"


class assertRaises:
    """
    Assert that something raises a particular type of error.

    The error raised must be a subclass of the expected_kls
    Have a message that matches the specified regex.

    And have atleast the values specified in it's kwargs.

    This is the same as fuzzyAssertRaisesError in DelfickErrorTestMixin
    but more suitable to use in pytest.

    .. code-block:: python

        from delficK-project.errors_pytest import assertRaises

        def test_something():
            error1 = DelfickError("something bad happend")
            with assertRaises(MyError, "nope", arg1=2, _errors=[error1]):
                raise MyError("nope", arg1=2, arg2=3, _errors=[error1])
    """

    def __init__(self, expected_kls, expected_msg_regex=Empty, **values):
        self.values = values
        self.expected_kls = expected_kls
        self.expected_msg_regex = expected_msg_regex
        if self.expected_msg_regex is not Empty:
            self.expected_msg_regex = RegexCompare(self.expected_msg_regex)

        self.errors = None
        if "_errors" in self.values:
            self.errors = self.values.pop("_errors")

    def __enter__(self):
        return

    def __exit__(self, exc_type, exc, tb):
        __tracebackhide__ = True

        if exc_type is None:
            info = {
                "expected_kls": self.expected_kls,
                "expected_msg_regex": self.expected_msg_regex,
                "values": self.values,
                "errors": self.errors,
            }
            assert False, dedent(
                """
                Expected an exception to be raised
                    expected_kls: {expected_kls}
                    expected_msg_regex: {expected_msg_regex}
                    have_atleast: {values}
                    errors: {errors}
            """.format(
                    **info
                )
            ).strip()

        try:
            assertSameError(
                exc, self.expected_kls, self.expected_msg_regex, self.values, self.errors
            )
        except:
            assertion = sys.exc_info()[1]

            print("!" * 20)
            print()
            print("Exception:")
            print(exc)
            print()
            print("Traceback:")
            lines = traceback.format_tb(tb)
            for line in lines:
                print(line)
            print()
            print("Expected:")
            print("  class: {0}".format(self.expected_kls))
            if self.expected_msg_regex is not Empty:
                print("  msg: {0}".format(self.expected_msg_regex))
            print("  values: {0}".format(self.values))
            if self.errors:
                print("  errors:")
                for e in self.errors:
                    print("    {0}".format(e))
            print()
            print("!" * 20)

            raise assertion from None

        return True


def assertSameError(error, expected_kls, expected_msg_regex, values, errors):
    """Assert that error is expected"""
    assert issubclass(error.__class__, expected_kls), "Error is wrong subclass"

    if not issubclass(error.__class__, DelfickError) and not getattr(
        error, "_fake_delfick_error", False
    ):
        # For normal exceptions we just regex against the string of the whole exception
        if expected_msg_regex is not Empty:
            assert expected_msg_regex == str(error), "Incorrect message"
    else:
        # For special DelfickError exceptions, we compare against error.message, error.kwargs and error._errors
        if expected_msg_regex is not Empty:
            assert expected_msg_regex == error.message, "Incorrect message"

        want_keys = set(values)
        got_keys = set(error.kwargs)
        assert want_keys <= got_keys, "Missing values"

        got_subset = {k: v for k, v in error.kwargs.items() if k in want_keys}
        assert values == got_subset, "Mismatched values"

        if errors:
            assert sorted(error.errors) == sorted(errors), "Errors list is different"
