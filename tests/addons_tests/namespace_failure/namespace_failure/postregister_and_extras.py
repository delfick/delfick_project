from delfick_project.addons import addon_hook


@addon_hook(post_register=True, extras=[("black.addons", "one")])
def hook(collector, result_maker, **kwargs):
    collector.configuration["resolved"].append((__name__,))
