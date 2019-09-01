from option_merge_addons import option_merge_addon_hook


@option_merge_addon_hook(extras=[])
def hook(collector, result_maker, **kwargs):
    collector.configuration["resolved"].append((__name__,))
    return result_maker(extras=[("blue.addons", "__all__")])


@option_merge_addon_hook(post_register=True)
def post_hook(collector, **kwargs):
    collector.configuration["post_register"].append((__name__, kwargs))
