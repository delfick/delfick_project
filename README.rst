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
   * option_merge is now under delfick_project.option_merge
   * input_algorithms is now under delfick_project.norms

     * many_item_formatted_spec is now under spec_base
     * you can now say ``from delfick_project.norms import sb`` instead
       of ``from input_algorithms import spec_base as sb``

   * the ``option_merge_addons.option_merge_addon_hook`` is now
     ``from delfick_project.addons import addon_hook`` and the default namespace
     it looks for is now ``delfick_project.addons`` rather than
     ``option_merge.addons``
