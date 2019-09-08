from delfick_project.addons import addon_hook

from addons_tests_register import global_register

global_register["imported"].append((__name__,))


@addon_hook(extras=[])
def hook(collector, result_maker, **kwargs):
    collector.configuration["resolved"].append((__name__,))
    return result_maker(extras=[("black.addons", "five")])


@addon_hook(post_register=True)
def post_hook(collector, **kwargs):
    collector.configuration["post_register"].append((__name__, kwargs))
