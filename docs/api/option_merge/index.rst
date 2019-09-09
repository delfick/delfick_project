.. module:: delfick_project.option_merge

.. _option_merge:

Option Merge
============

This provides the :class:`~delfick_project.option_merge.merge.MergedOptions`
class, which allows you to treat multiple python dictionaries as one.

Usage is either from the classmethod shortcut:

.. code-block:: python

    options = MergedOptions.using(options1, options2)

Or with the update method:

.. code-block:: python

    options = MergedOptions()
    options.update(options1)
    options.update(options2)

This object will otherwise behave like a dictionary. Note that When options are
added, copies are made.

When you delete a key, it removes it from the first dictionary it can find.
This means a key can change value when deleted rather than disappearing altogether

So:

.. code-block:: python

    options1 = {'a':{'b':1, 'c':3}, 'b':5}
    options2 = {'a':{'b':4, 'c':9}, 'd':7}
    options = MergedOptions.using(options1, options2)

    # options['a'] == MergedOptions(prefix='a', <same_options>, <same_overrides>)
    # options['a']['b'] == 4
    # options['a']['c'] == 9
    # options['d'] == 7

    del options['a']['c']
    # options['a']['c'] == 3

.. toctree::

    design
    api/index
