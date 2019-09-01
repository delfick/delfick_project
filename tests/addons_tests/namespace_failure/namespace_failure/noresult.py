from option_merge_addons import option_merge_addon_hook

@option_merge_addon_hook(extras=[])
def hook(collector, result_maker, **kwargs):
    collector.configuration["resolved"].append((__name__, ))
