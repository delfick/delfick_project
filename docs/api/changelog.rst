.. _changelog:

Changelog
---------

0.7.8 - TBD
   * Include LICENSE in the pypi package

0.7.7 - 13 December 2020
   * Make it possible to make silent default and have ``--unsilent`` instead
     of ``--silent``

0.7.6 - 27 November 2020
   * Fixed a memory leak

0.7.5 - 28 May 2020
   * Fixed a bug with json to console logs. It was writing {"msg": <message>}
     instead of just <message> like it should be.

0.7.4 - 9 March 2020
   * Import failure of resolving hooks doesn't hide the exception behind a
     BadHook exception.

0.7.3 - 4 January 2020
   * Made ``extra_files`` option to ``Collector#prepare`` take in dictionaries.

0.7.2 - 31 December 2019
   * The option_merge formatter will now let through ``None``

0.7.1 - 19 November 2019
   * ``--logging-program`` can now be specified at the same time as ``--silent``
     or ``--debug``

0.7.0 - 5 November 2019
   * fuzzyAssertRaisesError will now catch BaseExceptions like the pytest
     assertRaises does. Mainly so I can catch asyncio.CancelledError under
     Python 3.8.
   * delfick_project is now only compatible with Python versions greater than 3.6

0.6.0 - 14 October 2019
   * Ensure that as_dict on a dictobj or MergedOptions works if we have objects
     with an as_dict method that doesn't take in any parameters.

0.5.2 - 3 October 2019
   * Added an option --logging-handler-file for saying where logs should go to.
     This essentially defaults to sys.stderr

0.5.1 - 18 September 2019
   * Removed six import I didn't notice in migration

0.5 - 18 September 2019
   Moved the following projects into here

   * https://github.com/delfick/delfick_app
   * https://github.com/delfick/delfick_error
   * https://github.com/delfick/delfick_logging
   * https://github.com/delfick/option_merge
   * https://github.com/delfick/input_algorithms
   * https://github.com/delfick/layerz
   * https://github.com/delfick/option_merge_addons

   This is mostly a drop in replacement to including these projects

   Changes include:

   * Dropped support for python2
   * delfick_app is now under delfick_project.app

     * No boto integration in delfick_app
     * No command_output function in delfick_app
     * No DelayedFileType argparse helper as that's only necessary in python2.6
     * Added OptionalFileType that returns None if the file doesn't exist

   * delfick_error is now under delfick_project.errors and
     delfick_project.errors_pytest
   * delfick_logging is now under delfick_project.logging.

     * rainbow_logging_handler is now an optional dependency. If you want
       colourful logs then just install 'rainbow_logging_handler==2.2.2' in
       your python environment

   * option_merge is now under delfick_project.option_merge

     * The MergedOptionStringFormatter can be used as is and doesn't require
       being a subclass. This is because I can use DelfickError to implement
       the missing parts that had to be done by the user
     * The MergedOptionStringFormatter makes it easier to specify custom format
       specs. If you want a custom spec to not be formatted then specify it in
       a class attribute on your Formatter as passthrough_format_specs (which
       should be a list of strings). And just implement special_format_field. 
     * The MergedOptionStringFormatter ``__init__`` has changed signature and
       is just ``__init__(all_options, value, chain=None)``. To mimic the
       option_path option from before say something like
       ``MyFormatter(all_options, "{path}")`` instead of
       ``MyFormatter(all_options, "path")``

   * input_algorithms is now under delfick_project.norms

     * many_item_formatted_spec is now under spec_base
     * you can now say ``from delfick_project.norms import sb`` instead
       of ``from input_algorithms import spec_base as sb``
     * dictobj no longer has a dependency on the namedlist project

   * the ``option_merge_addons.option_merge_addon_hook`` is now
     ``from delfick_project.addons import addon_hook`` and the default namespace
     it looks for is now ``delfick_project.addons`` rather than
     ``option_merge.addons``

   * Resolving addons with delfick_project.addons will no longer intercept
     exceptions with a BadImport exception.

   * collector.register_converters now has a different signature. You just pass
     in a dictionary of ``{key: spec}`` where key is either a string or tuple
     of strings. So you don't need to tell it about the Meta or NotSpecified
     objects.
