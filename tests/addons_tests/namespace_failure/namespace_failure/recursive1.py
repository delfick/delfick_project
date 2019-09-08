from delfick_project.addons import addon_hook


@addon_hook(extras=[("failure.addons", "recursive2")])
def hook(collector, result_maker, **kwargs):
    collector.configuration["resolved"].append((__name__,))
    return result_maker()
