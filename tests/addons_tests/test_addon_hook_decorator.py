# coding: spec

from option_merge_addons import option_merge_addon_hook
from option_merge_addons import ProgrammerError

from tests.helpers import TestCase

import mock

describe TestCase, "option_merge_addon_hook":
    it "defaults extras to an empty dictionary and post_register to False":
        self.assertEqual(option_merge_addon_hook().extras, [])
        self.assertEqual(option_merge_addon_hook().post_register, False)

    it "complains if you set extras and post_register at the same time":
        with self.fuzzyAssertRaisesError(ProgrammerError, "Sorry, can't specify ``extras`` and ``post_register`` at the same time"):
            option_merge_addon_hook(extras={"option_merge.addon": "other"}, post_register=True)

    it "doesn't complain if you only set post_register":
        self.assertEqual(option_merge_addon_hook(post_register=True).post_register, True)

    it "doesn't complain if you only set extras":
        self.assertEqual(option_merge_addon_hook(extras=[("1", "2")]).extras, [("1", ["2"])])

    it "sets extras on the func passed in":
        def func(): pass
        extras = [("one", ["two"])]

        assert not hasattr(func, "extras")
        self.assertIs(option_merge_addon_hook(extras=extras)(func), func)
        self.assertEqual(func.extras, [("one", ["two"])])

    it "sets _option_merge_addon_entry to true on the func passed in":
        def func(): pass
        extras = []

        assert not hasattr(func, "_option_merge_addon_entry")
        option_merge_addon_hook(extras=extras)(func)
        self.assertIs(func._option_merge_addon_entry, True)

        func._option_merge_addon_entry = False
        self.assertIs(func._option_merge_addon_entry, False)
        self.assertIs(option_merge_addon_hook(post_register=True)(func), func)
        self.assertIs(func._option_merge_addon_entry, True)

    it "sets _option_merge_addon_entry_post_register to post_register on the func passed in":
        def func(): pass
        post_register = mock.Mock(name="post_register")

        assert not hasattr(func, "_option_merge_addon_entry_post_register")
        self.assertIs(option_merge_addon_hook(post_register=post_register)(func), func)
        self.assertIs(func._option_merge_addon_entry_post_register, post_register)

