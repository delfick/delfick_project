# coding: spec

from unittest import mock

import pytest

from delfick_project.addons import AddonGetter, Register


@pytest.fixture()
def global_register():
    from addons_tests_register import global_register

    return global_register


describe "order of import, resolution and post order":
    it "does it in the right order", global_register:
        global_register["imported"] = []
        addon_getter = AddonGetter()
        addon_getter.add_namespace("black.addons")
        addon_getter.add_namespace("green.addons")

        configuration = {"resolved": [], "post_register": []}
        collector = mock.Mock(name="collector", configuration=configuration)

        register = Register(addon_getter, collector)
        register.add_pairs(
            ("black.addons", "one"),
            ("black.addons", "two"),
            ("green.addons", "three"),
            ("green.addons", "four"),
        )

        assert global_register["imported"] == []
        register.recursive_import_known()

        assert global_register["imported"] == [
            ("namespace_black.one",),
            ("namespace_black.two",),
            ("namespace_green.three",),
            ("namespace_green.four",)
            # ---- ROUND 2 ---- #
            ,
            ("namespace_green.five",),
            ("namespace_black.six",),
            ("namespace_black.three",),
            ("namespace_green.nine",)
            # ---- ROUND 3 ---- #
            ,
            ("namespace_green.seven",)
            # ---- ROUND 4 ---- #
            ,
            ("namespace_black.eight",),
        ]

        found = [[key for key, _ in layer] for layer in register.layered]
        assert found == [
            [
                ("black.addons", "eight"),
                ("green.addons", "five"),
                ("black.addons", "three"),
                ("black.addons", "six"),
                ("green.addons", "four"),
            ],
            [("green.addons", "seven"), ("black.addons", "two")],
            [("green.addons", "nine")],
            [("green.addons", "three")],
            [("black.addons", "one")],
        ]

        assert configuration["resolved"] == []
        register.recursive_resolve_imported()

        assert global_register["imported"] == [
            ("namespace_black.one",),
            ("namespace_black.two",),
            ("namespace_green.three",),
            ("namespace_green.four",)
            # ---- ROUND 2 ---- #
            ,
            ("namespace_green.five",),
            ("namespace_black.six",),
            ("namespace_black.three",),
            ("namespace_green.nine",)
            # ---- ROUND 3 ---- #
            ,
            ("namespace_green.seven",)
            # ---- ROUND 4 ---- #
            ,
            ("namespace_black.eight",)
            # ---- POST RESOLVE ---- #
            # ---- ROUND 5 ---- #
            ,
            # black six
            ("namespace_black.four",),
            # green four
            ("namespace_black.ten",),
            # green three
            ("namespace_green.ten",),
            # black one
            ("namespace_black.seven",)
            # ---- ROUND 6 ---- #
            ,
            # black 10
            ("namespace_black.five",),
        ]

        found = [[key for key, _ in layer] for layer in register.layered]
        assert found == [
            [
                ("black.addons", "eight"),
                ("black.addons", "five"),
                ("black.addons", "four"),
                ("green.addons", "five"),
                ("black.addons", "three"),
                ("green.addons", "ten"),
            ],
            [
                ("black.addons", "seven"),
                ("black.addons", "ten"),
                ("green.addons", "seven"),
                ("black.addons", "six"),
            ],
            [("green.addons", "four"), ("black.addons", "two")],
            [("green.addons", "nine")],
            [("green.addons", "three")],
            [("black.addons", "one")],
        ]

        # Now we post_register
        register.post_register(
            {"black.addons": dict(one=1, two=2), "green.addons": dict(three=3, four=4)}
        )
        assert configuration["post_register"] == [
            ("namespace_black.eight", {"two": 2, "one": 1}),
            ("namespace_black.five", {"two": 2, "one": 1}),
            ("namespace_black.four", {"two": 2, "one": 1}),
            ("namespace_green.five", {"three": 3, "four": 4}),
            ("namespace_black.three", {"two": 2, "one": 1}),
            ("namespace_green.ten", {"three": 3, "four": 4}),
            ("namespace_black.seven", {"two": 2, "one": 1}),
            ("namespace_black.ten", {"two": 2, "one": 1}),
            ("namespace_green.seven", {"three": 3, "four": 4}),
            ("namespace_black.six", {"two": 2, "one": 1}),
            ("namespace_green.four", {"three": 3, "four": 4}),
            ("namespace_black.two", {"two": 2, "one": 1}),
            ("namespace_green.nine", {"three": 3, "four": 4}),
            ("namespace_green.three", {"three": 3, "four": 4}),
            ("namespace_black.one", {"two": 2, "one": 1}),
        ]

    describe "special __all__":
        it "getting __all__ from the start":
            addon_getter = AddonGetter()
            addon_getter.add_namespace("blue.addons")

            configuration = {"resolved": [], "post_register": []}
            collector = mock.Mock(name="collector", configuration=configuration)

            register = Register(addon_getter, collector)
            register.add_pairs(("blue.addons", "one"))

            register.recursive_import_known()

            found = [[key for key, _ in layer] for layer in register.layered]
            assert found == [
                [("blue.addons", "five"), ("blue.addons", "six")],
                [("blue.addons", "four"), ("blue.addons", "three")],
                [("blue.addons", "two")],
                [("blue.addons", "one")],
            ]

            assert configuration["resolved"] == []
            register.recursive_resolve_imported()

            found = [[key for key, _ in layer] for layer in register.layered]
            assert found == [
                [("blue.addons", "five"), ("blue.addons", "six")],
                [("blue.addons", "four"), ("blue.addons", "three")],
                [("blue.addons", "two")],
                [("blue.addons", "one")],
            ]

            # Now we post_register
            register.post_register({"blue.addons": dict(one=1, two=2)})
            assert configuration["post_register"] == [
                ("namespace_blue.five", {"two": 2, "one": 1}),
                ("namespace_blue.six", {"two": 2, "one": 1}),
                ("namespace_blue.four", {"two": 2, "one": 1}),
                ("namespace_blue.three", {"two": 2, "one": 1}),
                ("namespace_blue.two", {"two": 2, "one": 1}),
                ("namespace_blue.one", {"two": 2, "one": 1}),
            ]

        it "getting __all__ from the result_maker":
            addon_getter = AddonGetter()
            addon_getter.add_namespace("blue.addons")

            configuration = {"resolved": [], "post_register": []}
            collector = mock.Mock(name="collector", configuration=configuration)

            register = Register(addon_getter, collector)
            register.add_pairs(("blue.addons", "six"))

            register.recursive_import_known()

            found = [[key for key, _ in layer] for layer in register.layered]
            assert found == [[("blue.addons", "six")]]

            assert configuration["resolved"] == []
            register.recursive_resolve_imported()

            found = [[key for key, _ in layer] for layer in register.layered]
            assert found == [
                [("blue.addons", "five"), ("blue.addons", "one")],
                [("blue.addons", "four"), ("blue.addons", "three")],
                [("blue.addons", "two")],
                [("blue.addons", "six")],
            ]

            # Now we post_register
            register.post_register({"blue.addons": dict(one=1, two=2)})
            assert configuration["post_register"] == [
                ("namespace_blue.five", {"two": 2, "one": 1}),
                ("namespace_blue.one", {"two": 2, "one": 1}),
                ("namespace_blue.four", {"two": 2, "one": 1}),
                ("namespace_blue.three", {"two": 2, "one": 1}),
                ("namespace_blue.two", {"two": 2, "one": 1}),
                ("namespace_blue.six", {"two": 2, "one": 1}),
            ]
