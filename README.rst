Project helpers
===============

This is a collection of code that I use in nearly all my projects:

* Mainline helper
* Custom python exception class
* Logging helpers
* Option merging
* Validation and Normalisation of data
* Module addon system

It started as a monorepo of these projects:

* https://github.com/delfick/delfick_app
* https://github.com/delfick/delfick_error
* https://github.com/delfick/delfick_logging
* https://github.com/delfick/option_merge
* https://github.com/delfick/input_algorithms
* https://github.com/delfick/layerz
* https://github.com/delfick/option_merge_addons

Changelog
---------

0.5 - TBD
   Mostly drop in replacement to including the delfick_app, delfick_error,
   delfick_logging, option_merge and input_algorithms in your project.

   Changes include:

   * Dropped support for python2
   * delfick_app is now under delfick_project.app

     * No boto integration in delfick_app
     * No command_output function in delfick_app
     * No DelayedFileType argparse helper as that's only necessary in python2.6

   * delfick_error is now under delfick_project.errors and
     delfick_project.errors_pytest
   * delfick_logging is now under delfick_project.logging.

     * rainbow_logging_handler is now an optional dependency. If you want
       colourful logs then just install 'rainbow_logging_handler==2.2.2' in
       your python environment

   * option_merge is now under delfick_project.option_merge
   * input_algorithms is now under delfick_project.norms

     * many_item_formatted_spec is now under spec_base
     * you can now say ``from delfick_project.norms import sb`` instead
       of ``from input_algorithms import spec_base as sb``
     * dictobj no longer has a dependency on the namedlist project

   * the ``option_merge_addons.option_merge_addon_hook`` is now
     ``from delfick_project.addons import addon_hook`` and the default namespace
     it looks for is now ``delfick_project.addons`` rather than
     ``option_merge.addons``

   * collector.register_converters now has a different signature. You just pass
     in a dictionary of ``{key: spec}`` where key is either a string or tuple
     of strings. So you don't need to tell it about the Meta or NotSpecified
     objects.
