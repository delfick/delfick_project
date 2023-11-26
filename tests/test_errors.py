# coding: spec

import random
import uuid
from unittest import TestCase, mock

from delfick_project.errors import DelfickError, DelfickErrorTestMixin
from delfick_project.errors_pytest import assertRaises


# Used in the tests
class AError(DelfickError):
    pass


class BError(DelfickError):
    pass


class CError(DelfickError):
    pass


describe "DelfickError":
    it "creates a message that combines desc on the class, args and kwargs":
        error = DelfickError("The syncing was bad", a=4, b=5)
        assert str(error) == '"The syncing was bad"\ta=4\tb=5'
        assert error.as_dict() == {"message": "The syncing was bad", "a": 4, "b": 5}

    it "Works without a message":
        error = DelfickError(a_thing=4, b=5)
        assert str(error) == "a_thing=4\tb=5"
        assert error.as_dict() == {"a_thing": 4, "b": 5}

    it "works with subclasses of DelfickError":

        class OtherSyncingErrors(DelfickError):
            desc = "Oh my!"

        error = OtherSyncingErrors("hmmm", d=8, e=9)
        assert str(error) == '"Oh my!. hmmm"\td=8\te=9'
        assert error.as_dict() == {"message": "Oh my!. hmmm", "d": 8, "e": 9}

        error2 = OtherSyncingErrors(f=10, g=11)
        assert str(error2) == '"Oh my!"\tf=10\tg=11'
        assert error2.as_dict() == {"message": "Oh my!", "f": 10, "g": 11}

    it "can tell if an error is equal to another error":

        class Sub1(DelfickError):
            desc = "sub"

        class Sub2(DelfickError):
            desc = "sub"

        assert Sub1("blah") != Sub2("blah")
        assert Sub1("blah", one=1) != Sub1("blah", one=2)

        assert Sub1("blah") == Sub1("blah")
        assert Sub1("blah", one=1, two=2) == Sub1("blah", two=2, one=1)

    it "can tell if an error is equal to another error using delfick_error_format":

        class Sub1(DelfickError):
            desc = "sub"

        class Thing(object):
            def __init__(self, val):
                self.val = val

        assert Sub1("blah") == Sub1("blah")
        assert Sub1("blah", one=Thing(1)) != Sub1("blah", one=Thing(1))

        class BetterThing(Thing):
            def delfick_error_format(self, key):
                return "{0}:{1}".format(key, self.val)

        assert Sub1("blah", one=BetterThing(1)) == Sub1("blah", one=BetterThing(1))

    it "treats _errors as a special kwarg":
        error1 = str(uuid.uuid1())
        error1_as_dict = uuid.uuid1()

        error2 = str(uuid.uuid1())
        error2_as_dict = uuid.uuid1()

        class error1_obj(object):
            def __str__(self):
                return error1

            def as_dict(self):
                return error1_as_dict

        class error2_obj(object):
            def __str__(self):
                return error2

            def as_dict(self):
                return error2_as_dict

        errors = [error1_obj(), error2_obj()]

        error = DelfickError("hmmm", _errors=errors)
        assert error.errors == errors
        assert "_errors" not in error.kwargs

        assert str(error) == '"hmmm"\nerrors:\n=======\n\n\t{0}\n-------\n\t{1}\n-------'.format(
            error1, error2
        )
        assert error.as_dict() == {"message": "hmmm", "errors": [error1_as_dict, error2_as_dict]}

    it "can format special values":

        class WithFormat(object):
            def __init__(self, val):
                self.val = val

            def delfick_error_format(self, key):
                return "formatted_{0}_{1}".format(key, self.val)

        wf1 = WithFormat(1)
        wf2 = WithFormat(2)
        error = DelfickError(blah=wf1, meh=wf2, things=3)
        assert str(error) == "blah=formatted_blah_1\tmeh=formatted_meh_2\tthings=3"
        assert error.as_dict() == {
            "blah": "formatted_blah_1",
            "meh": "formatted_meh_2",
            "things": 3,
        }

        assert error.as_tuple()[2] == (("blah", wf1), ("meh", wf2), ("things", 3))
        assert error.as_tuple(formatted=True)[2] == (
            ("blah", "formatted_blah_1"),
            ("meh", "formatted_meh_2"),
            ("things", 3),
        )

    it "is hashable":
        e0 = BError("e0")
        e1 = AError("e1", one=2, _errors=[e0])
        e2 = CError(three=4)
        assert sorted({e0: 1, e1: 1, e2: 3}.items()) == sorted([(e0, 1), (e1, 1), (e2, 3)])

    describe "formatted_val":
        it "just returns val if has no delfick_error_format attribute":
            key = mock.Mock(name="key")
            assert DelfickError().formatted_val(key, 3) == 3

        it "returns result of calling delfick_error_format if it has one":
            key = mock.Mock(name="key")
            thing = mock.Mock(name="thing")
            thing.delfick_error_format.return_value = 50

            assert DelfickError().formatted_val(key, thing) == 50

        it "passes in the key to delfick_error_format":
            key = mock.Mock(name="key")
            thing = mock.Mock(name="thing")
            thing.delfick_error_format.return_value = 50

            assert DelfickError().formatted_val(key, thing) == 50
            thing.delfick_error_format.assert_called_once_with(key)

        it "catches any exception from delfick_error_format":
            key = mock.Mock(name="key")
            error = DelfickError("blah")
            thing = mock.Mock(name="thing")
            thing.delfick_error_format.side_effect = error

            assert DelfickError().formatted_val(
                key, thing
            ) == "<|Failed to format val for exception: val={0}, error={1}|>".format(thing, error)

    describe "Sorting":

        def assertSorted(self, *errors):
            """Shuffle the provided errors and make sure they always get sorted into the provided order"""
            expected = list(errors)
            errors = list(errors)
            print("Expect result of {0}".format(expected))
            print("---")

            def compare(attmpt):
                print("Sorting {0}".format(attmpt))
                sortd = sorted(attmpt)
                print("Got {0}".format(sortd))
                assert sortd == expected
                print("===")

            for attempt in (errors, list(reversed(errors))):
                compare(attempt)

            for _ in range(5):
                random.shuffle(errors)
                compare(errors)

        it "sorts based on class first":
            self.assertSorted(AError("b"), BError("d"), CError("a"))

            self.assertSorted(AError("b", b=2), BError("a", a=1))

            self.assertSorted(AError("b", c=3, _errors=[3, 4]), CError("a", c=2, _errors=[1, 2]))

        it "sorts on message second":
            self.assertSorted(
                AError("zadf"), AError("zsdf"), BError("gd"), BError("he"), CError("a")
            )

        it "sorts on kwargs third":
            self.assertSorted(
                AError("zsdf", b=2, c=3),
                BError("zsdf", a=1),
                BError("zsdf", a=2, b=4),
                CError("zsdf", c=1),
            )

        it "sorts on errors last":
            self.assertSorted(
                AError("asdf", a=1, _errors=[5, 4]),
                AError("asdf", a=1, _errors=[6, 1]),
                BError("asdf", a=1, _errors=[1, 2]),
                BError("asdf", a=1, _errors=[1, 2, 1]),
            )

# Some objects for my expecting_raised_assertion helper
class Called(object):
    pass


class BeforeManager(object):
    pass


class InsideManager(object):
    pass


class AssertionRaised(object):
    pass


class NoAssertionRaised(object):
    pass


class NonAssertionRaised(object):
    pass


class DelfickErrorCase(TestCase, DelfickErrorTestMixin):
    __test__ = False

    def runTest(self, *args, **kwargs):
        pass


describe "Tests mixin":
    describe "Fuzzy assert raises":

        def expecting_raised_assertion(self, *args, **kwargs):
            """Yield (iterator, val) from _expecting_raised_assertion"""
            iterator = self._expecting_raised_assertion(*args, **kwargs)
            while True:
                try:
                    val = next(iterator)
                except StopIteration:
                    break

                yield iterator, val

        def _expecting_raised_assertion(self, called, *args, **kwargs):
            """Assert that an assertion is raised and yield that assertion for more checks"""
            buf = []
            called.append(BeforeManager)
            yield (BeforeManager, None)
            try:
                with DelfickErrorCase().fuzzyAssertRaisesError(*args, **kwargs):
                    called.append(InsideManager)
                    for_raising = yield (InsideManager, None)
                    if for_raising:
                        raise for_raising
                called.append(NoAssertionRaised)
                yield (NoAssertionRaised, None)
            except AssertionError as error:
                print("Assertion raised: '{0}: {1}'".format(error.__class__, error))
                called.append(AssertionRaised)
                buf.append((AssertionRaised, error))
            except Exception as error:
                print("Non assertion raised: '{0}: {1}'".format(error.__class__, error))
                called.append(NonAssertionRaised)
                buf.append((NonAssertionRaised, error))

            # For some reason these values don't come through
            # Unless I yield something before them
            # Outside of the catch blocks...
            # *keeps calm and carries on*
            yield (None, None)
            for val in buf:
                yield val

            # Yield called for sanity checks
            yield (Called, called)

        it "complains if no exception is raised":
            called = []
            for iterator, (part, val) in self.expecting_raised_assertion(called, Exception):
                if part is InsideManager:
                    pass
                elif part is AssertionRaised:
                    assert str(val).startswith("Expected an exception to be raised"), str(val)
            assert called == [BeforeManager, InsideManager, AssertionRaised]

        it "complains if exception is not a subclass of what is expected":
            raised = TypeError("ERROR!")

            called = []
            for iterator, (part, val) in self.expecting_raised_assertion(called, ValueError):
                if part is InsideManager:
                    iterator.send(raised)
                elif part is AssertionRaised:
                    assert str(val) == "Expected {0}, got {1}".format(ValueError, TypeError)

            assert called == [BeforeManager, InsideManager, AssertionRaised]

        it "complains if exception is subclass but doesn't match regex":

            class Raised(ValueError):
                pass

            raised = Raised("blah")

            called = []
            for iterator, (part, val) in self.expecting_raised_assertion(called, ValueError, "meh"):
                if part is InsideManager:
                    iterator.send(raised)
                elif part is AssertionRaised:
                    assert str(val) == "Regex didn't match: 'meh' not found in 'blah'"

            assert called == [BeforeManager, InsideManager, AssertionRaised]

        it "works fine if regex and subclass match":

            class Expected(IndexError):
                pass

            class Raised(Expected):
                pass

            raised = Raised("stuff")

            called = []
            for iterator, (part, val) in self.expecting_raised_assertion(called, Expected, "stuff"):
                if part is InsideManager:
                    iterator.send(raised)

            assert called == [BeforeManager, InsideManager, NoAssertionRaised]

        describe "For DelfickError exceptions":
            it "works on fake DelfickError class":

                class Expected(Exception):
                    def __init__(s, message, kwarg1):
                        s.message = message
                        s.kwarg1 = kwarg1
                        s.kwargs = dict(kwarg1=kwarg1)
                        s._fake_delfick_error = True

                    def __str__(s):
                        return "Expected: {0}\tkwarg1={1}".format(s.message, s.kwarg1)

                called = []
                for iterator, (part, val) in self.expecting_raised_assertion(
                    called, Expected, "something", kwarg1="meh"
                ):
                    if part is InsideManager:
                        iterator.send(Expected("something", kwarg1="meh"))

                assert called == [BeforeManager, InsideManager, NoAssertionRaised]

                called = []
                for iterator, (part, val) in self.expecting_raised_assertion(
                    called, Expected, "something", kwarg1="meh"
                ):
                    if part is InsideManager:
                        iterator.send(Expected("something", kwarg1="other"))
                    elif part is AssertionRaised:
                        assert str(val) == """Mismatched: {'kwarg1': expected='meh', got='other'}"""

                assert called == [BeforeManager, InsideManager, AssertionRaised]

            it "complains if any given kwargs doesn't match":

                class Expected(DelfickError):
                    pass

                called = []
                for iterator, (part, val) in self.expecting_raised_assertion(
                    called, Expected, one=1, two=1, three=1
                ):
                    if part is InsideManager:
                        iterator.send(Expected(one=1, two=2, three=3))
                    elif part is AssertionRaised:
                        assert (
                            str(val)
                            == "Mismatched: {'three': expected=1, got=3}, {'two': expected=1, got=2}"
                        )

                assert called == [BeforeManager, InsideManager, AssertionRaised]

            it "complains about any missing kwargs from what we specify":

                class Expected(DelfickError):
                    pass

                called = []
                for iterator, (part, val) in self.expecting_raised_assertion(
                    called, Expected, one=1, three=1, four=1
                ):
                    if part is InsideManager:
                        iterator.send(Expected(one=1))
                    elif part is AssertionRaised:
                        assert str(val) == "Missing: 'four', 'three'"

                assert called == [BeforeManager, InsideManager, AssertionRaised]

            it "doesn't care about extra kwargs in what was raised":

                class Expected(DelfickError):
                    pass

                called = []
                for iterator, (part, val) in self.expecting_raised_assertion(
                    called, Expected, one=1
                ):
                    if part is InsideManager:
                        iterator.send(Expected(one=1, two=2))

                assert called == [BeforeManager, InsideManager, NoAssertionRaised]

            it "complains about message before kwargs":

                class Expected(DelfickError):
                    desc = "expected"

                class Raised(Expected):
                    desc = "raised"

                called = []
                for iterator, (part, val) in self.expecting_raised_assertion(
                    called, Raised, "testing, 1.. 2.. 3", one=1, three=2
                ):
                    if part is InsideManager:
                        iterator.send(Raised("testing for great good", one=1, three=3))
                    elif part is AssertionRaised:
                        assert (
                            str(val)
                            == "Regex didn't match: 'testing, 1.. 2.. 3' not found in 'testing for great good'"
                        )

                assert called == [BeforeManager, InsideManager, AssertionRaised]

            it "complains if errors aren't the same":

                class Expected(DelfickError):
                    pass

                called = []
                for iterator, (part, val) in self.expecting_raised_assertion(
                    called, Expected, one=1, _errors=[3, 5, 10, 4]
                ):
                    if part is InsideManager:
                        iterator.send(Expected(one=1, two=2, _errors=[20, 5, 4, 3]))
                    elif part is AssertionRaised:
                        assert "[3, 4, 5, 20] != [3, 4, 5, 10]" in str(val), str(val)

                assert called == [BeforeManager, InsideManager, AssertionRaised]

            it "does a sorted comparison of the errors":

                class Expected(DelfickError):
                    pass

                called = []
                for iterator, (part, val) in self.expecting_raised_assertion(
                    called, Expected, one=1, _errors=[3, 5, 10, 4]
                ):
                    if part is InsideManager:
                        iterator.send(Expected(one=1, two=2, _errors=[10, 5, 4, 3]))

                assert called == [BeforeManager, InsideManager, NoAssertionRaised]

            it "does a sorted comparison of the errors taking delfick_error_format objects into account":

                class Expected(DelfickError):
                    pass

                class Thing(object):
                    def __init__(s, val):
                        s.val = val

                    def delfick_error_format(s, key):
                        return "{0}:{1}".format(key, s.val)

                class Error(DelfickError):
                    pass

                e = lambda val: Error(thing=Thing(val))

                called = []
                for iterator, (part, val) in self.expecting_raised_assertion(
                    called, Expected, one=1, _errors=[e(3), e(5), e(10), e(4)]
                ):
                    if part is InsideManager:
                        iterator.send(Expected(one=1, two=2, _errors=[e(10), e(5), e(4), e(3)]))

                assert called == [BeforeManager, InsideManager, NoAssertionRaised]

describe "standalone assert raises":

    def expecting_raised_assertion(self, *args, **kwargs):
        """Yield (iterator, val) from _expecting_raised_assertion"""
        iterator = self._expecting_raised_assertion(*args, **kwargs)
        while True:
            try:
                val = next(iterator)
            except StopIteration:
                break
            yield iterator, val

    def _expecting_raised_assertion(self, called, *args, **kwargs):
        """Assert that an assertion is raised and yield that assertion for more checks"""

        buf = []
        called.append(BeforeManager)
        yield (BeforeManager, None)
        try:
            with assertRaises(*args, **kwargs):
                called.append(InsideManager)
                for_raising = yield (InsideManager, None)
                if for_raising:
                    raise for_raising
            called.append(NoAssertionRaised)
            yield (NoAssertionRaised, None)
        except AssertionError as error:
            print("Assertion raised: '{0}: {1}'".format(error.__class__, error))
            called.append(AssertionRaised)
            buf.append((AssertionRaised, error))
        except Exception as error:
            print("Non assertion raised: '{0}: {1}'".format(error.__class__, error))
            called.append(NonAssertionRaised)
            buf.append((NonAssertionRaised, error))

        # For some reason these values don't come through
        # Unless I yield something before them
        # Outside of the catch blocks...
        # *keeps calm and carries on*
        yield (None, None)
        for val in buf:
            yield val

        # Yield called for sanity checks
        yield (Called, called)

    it "complains if no exception is raised":
        called = []
        for iterator, (part, val) in self.expecting_raised_assertion(called, Exception):
            if part is InsideManager:
                pass
            elif part is AssertionRaised:
                assert str(val).startswith("Expected an exception to be raised"), str(val)
        assert called == [BeforeManager, InsideManager, AssertionRaised]

    it "complains if exception is not a subclass of what is expected":
        raised = TypeError("ERROR!")

        called = []
        for iterator, (part, val) in self.expecting_raised_assertion(called, ValueError):
            if part is InsideManager:
                iterator.send(raised)
            elif part is AssertionRaised:
                assert str(val) == "Error is wrong subclass"

        assert called == [BeforeManager, InsideManager, AssertionRaised]

    it "complains if exception is subclass but doesn't match regex":

        class Raised(ValueError):
            pass

        raised = Raised("blah")

        called = []
        for iterator, (part, val) in self.expecting_raised_assertion(called, ValueError, "meh"):
            if part is InsideManager:
                iterator.send(raised)
            elif part is AssertionRaised:
                assert str(val) == "Incorrect message"

        assert called == [BeforeManager, InsideManager, AssertionRaised]

    it "works fine if regex and subclass match":

        class Expected(IndexError):
            pass

        class Raised(Expected):
            pass

        raised = Raised("stuff")

        called = []
        for iterator, (part, val) in self.expecting_raised_assertion(called, Expected, "stuff"):
            if part is InsideManager:
                iterator.send(raised)

        assert called == [BeforeManager, InsideManager, NoAssertionRaised]

    describe "For DelfickError exceptions":
        it "works on fake DelfickError class":

            class Expected(Exception):
                def __init__(self, message, kwarg1):
                    self.message = message
                    self.kwarg1 = kwarg1
                    self.kwargs = dict(kwarg1=kwarg1)
                    self._fake_delfick_error = True

                def __str__(self):
                    return "Expected: {0}\tkwarg1={1}".format(self.message, self.kwarg1)

            called = []
            for iterator, (part, val) in self.expecting_raised_assertion(
                called, Expected, "something", kwarg1="meh"
            ):
                if part is InsideManager:
                    iterator.send(Expected("something", kwarg1="meh"))

            assert called == [BeforeManager, InsideManager, NoAssertionRaised]

            called = []
            for iterator, (part, val) in self.expecting_raised_assertion(
                called, Expected, "something", kwarg1="meh"
            ):
                if part is InsideManager:
                    iterator.send(Expected("something", kwarg1="other"))
                elif part is AssertionRaised:
                    assert str(val) == "Mismatched values"

            assert called == [BeforeManager, InsideManager, AssertionRaised]

        it "complains if any given kwargs doesn't match":

            class Expected(DelfickError):
                pass

            called = []
            for iterator, (part, val) in self.expecting_raised_assertion(
                called, Expected, one=1, two=1, three=1
            ):
                if part is InsideManager:
                    iterator.send(Expected(one=1, two=2, three=3))
                elif part is AssertionRaised:
                    assert str(val) == "Mismatched values"

            assert called == [BeforeManager, InsideManager, AssertionRaised]

        it "complains about any missing kwargs from what we specify":

            class Expected(DelfickError):
                pass

            called = []
            for iterator, (part, val) in self.expecting_raised_assertion(
                called, Expected, one=1, three=1, four=1
            ):
                if part is InsideManager:
                    iterator.send(Expected(one=1))
                elif part is AssertionRaised:
                    assert str(val) == "Missing values"

            assert called == [BeforeManager, InsideManager, AssertionRaised]

        it "doesn't care about extra kwargs in what was raised":

            class Expected(DelfickError):
                pass

            called = []
            for iterator, (part, val) in self.expecting_raised_assertion(called, Expected, one=1):
                if part is InsideManager:
                    iterator.send(Expected(one=1, two=2))

            assert called == [BeforeManager, InsideManager, NoAssertionRaised]

        it "complains about message before kwargs":

            class Expected(DelfickError):
                desc = "expected"

            class Raised(Expected):
                desc = "raised"

            called = []
            for iterator, (part, val) in self.expecting_raised_assertion(
                called, Raised, "testing, 1.. 2.. 3", one=1, three=2
            ):
                if part is InsideManager:
                    iterator.send(Raised("testing for great good", one=1, three=3))
                elif part is AssertionRaised:
                    assert str(val) == "Incorrect message"

            assert called == [BeforeManager, InsideManager, AssertionRaised]

        it "complains if errors aren't the same":

            class Expected(DelfickError):
                pass

            called = []
            for iterator, (part, val) in self.expecting_raised_assertion(
                called, Expected, one=1, _errors=[3, 5, 10, 4]
            ):
                if part is InsideManager:
                    iterator.send(Expected(one=1, two=2, _errors=[20, 5, 4, 3]))
                elif part is AssertionRaised:
                    assert str(val) == "Errors list is different"

            assert called == [BeforeManager, InsideManager, AssertionRaised]

        it "does a sorted comparison of the errors":

            class Expected(DelfickError):
                pass

            called = []
            for iterator, (part, val) in self.expecting_raised_assertion(
                called, Expected, one=1, _errors=[3, 5, 10, 4]
            ):
                if part is InsideManager:
                    iterator.send(Expected(one=1, two=2, _errors=[10, 5, 4, 3]))

            assert called == [BeforeManager, InsideManager, NoAssertionRaised]

        it "does a sorted comparison of the errors taking delfick_error_format objects into account":

            class Expected(DelfickError):
                pass

            class Thing(object):
                def __init__(self, val):
                    self.val = val

                def delfick_error_format(self, key):
                    return "{0}:{1}".format(key, self.val)

            class Error(DelfickError):
                pass

            e = lambda val: Error(thing=Thing(val))

            called = []
            for iterator, (part, val) in self.expecting_raised_assertion(
                called, Expected, one=1, _errors=[e(3), e(5), e(10), e(4)]
            ):
                if part is InsideManager:
                    iterator.send(Expected(one=1, two=2, _errors=[e(10), e(5), e(4), e(3)]))

            assert called == [BeforeManager, InsideManager, NoAssertionRaised]
