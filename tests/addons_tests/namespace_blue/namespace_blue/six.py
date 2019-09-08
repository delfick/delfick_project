from delfick_project.addons import addon_hook


@addon_hook(extras=[])
def hook(collector, result_maker, **kwargs):
    collector.configuration["resolved"].append((__name__,))
    return result_maker(extras=[("blue.addons", "__all__")])


@addon_hook(post_register=True)
def post_hook(collector, **kwargs):
    collector.configuration["post_register"].append((__name__, kwargs))
