from delfick_project.addons import addon_hook


@addon_hook(extras=[])
def hook(collector, result_maker, **kwargs):
    import wasdf
