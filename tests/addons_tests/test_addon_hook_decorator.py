# coding: spec

from unittest import mock

from delfick_project.addons import addon_hook
from delfick_project.errors import ProgrammerError
from delfick_project.errors_pytest import assertRaises

describe "addon_hook":
    it "defaults extras to an empty dictionary and post_register to False":
        assert addon_hook().extras == []
        assert addon_hook().post_register is False

    it "complains if you set extras and post_register at the same time":
        with assertRaises(
            ProgrammerError,
            "Sorry, can't specify ``extras`` and ``post_register`` at the same time",
        ):
            addon_hook(extras={"option_merge.addon": "other"}, post_register=True)

    it "doesn't complain if you only set post_register":
        assert addon_hook(post_register=True).post_register is True

    it "doesn't complain if you only set extras":
        assert addon_hook(extras=[("1", "2")]).extras == [("1", ["2"])]

    it "sets extras on the func passed in":

        def func():
            pass

        extras = [("one", ["two"])]

        assert not hasattr(func, "extras")
        assert addon_hook(extras=extras)(func) is func
        assert func.extras == [("one", ["two"])]

    it "sets _addon_hook to true on the func passed in":

        def func():
            pass

        extras = []

        assert not hasattr(func, "_delfick_project_addon_entry ")
        addon_hook(extras=extras)(func)
        assert func._delfick_project_addon_entry is True

        func._delfick_project_addon_entry = False
        assert func._delfick_project_addon_entry is False
        assert addon_hook(post_register=True)(func) is func
        assert func._delfick_project_addon_entry is True

    it "sets _delfick_project_addon_entry_post_register to post_register on the func passed in":

        def func():
            pass

        post_register = mock.Mock(name="post_register")

        assert not hasattr(func, "_delfick_project_addon_entry_post_register")
        assert addon_hook(post_register=post_register)(func) is func
        assert func._delfick_project_addon_entry_post_register is post_register
