.. _collector:

Collector
=========

.. automodule:: delfick_project.option_merge.collector

Hooks
-----

.. autoclass:: Collector
    :members: BadFileErrorKls, BadConfigurationErrorKls
              , alter_clone_args_dict, find_missing_config, extra_prepare, extra_prepare_after_activation, home_dir_configuration_location
              , read_file, start_configuration, add_configuration, extra_configuration_collection, setup

Usage
-----

.. automethod:: Collector.prepare

.. automethod:: Collector.clone

.. automethod:: Collector.register_converters
