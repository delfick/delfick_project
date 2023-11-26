.. _addons:

Addon Manager
=============

There are two parts to using this module: the setup, and the addons.

Setup
-----

.. code-block:: python

    from delfick_project.addons import Result, Addon, Register, AddonGetter

    # collector is passed into the hooks. It may be None
    # It's expected to a delfick_project.option_merge.Collector instance
    collector = None

    # Create the addon getter and register our namespace
    addon_getter = AddonGetter()
    addon_getter.add_namespace("my_amazing_addons", Result.FieldSpec(), Addon.FieldSpec())

    # Initiate the addons from our configuration
    register = Register(addon_getter, collector)

    # Register and execute our addons
    # This will import the my_amazing_addons.name1 addon, which will bring in it's dependencies
    # and so on
    # And then run the post_register hooks with {"arg": 1, "arg2": 2} as kwargs
    start_addons = [("my_amazing_addons", "name1")]
    register.register(*start_addons, my_amazing_addons={"arg1": 1, "arg2": 2})

Note that you can split up that last line into different stages you run at
different times with whatever you want before. This is helpful if you want to
do something before calling the post_register hooks:

.. code-block:: python

    # Add atleast one entry point that will start importing other entry points
    default_addons = [("my_amazing_addons", "name1"), ("my_amazing_addons", "name2")]
    register.add_pairs(*default_addons)

    # Import our addons
    register.recursive_import_known()

    # Resolve our addons
    register.recursive_resolve_imported()

    # extra_args specifies what goes into the post_register hooks
    extra_args = {"my_amazing_addons": {"arg1": 1}}
    self.register.post_register(extra_args)

Defining hooks
--------------

There are two parts to defining a hook. The first part is to define it:

.. code-block:: python

    from delfick_project.addons import addon_hook

    @addon_hook(extras=[('my_amazing_addons', 'thing1'), ('my_amazing_addons', 'thing2')])
    def __addon__(collector, results_maker, **kwargs):
        # Setup things here
        # We can return None or we can use results_maker to programmatically
        # add more dependencies
        return results_maker(extras=[("my_amazing_addons", "thing3")])

    @addon_hook(post_register=True)
    def __addon_post__(collector, **kwargs):
        # Setup that must be done after all dependencies have been resolved
        # And imported and had their first hook executed

The second part is to define the entry points in your setup.py. So if the above
hooks was at ``my_amazing_module.addons`` then your setup.py would look like:

.. code-block:: python

    from setuptools import setup

    setup(
          ...

          , entry_points =
            { "my_amazing_addons": ["amazing = my_amazing_module.addon"]
            }
        )

Once this package is installed in your environment, you may depend on it by
specifying ``("my_amazing_addons", "amazing")``.

Import Order
------------

The several passes of importing modules goes as follows:

1. Import all our known hooks
2. Keep importing all the dependencies that we find
3. Once we've imported everything, start calling the hooks and add any dependencies
   returned by the hooks to our known addons.
4. Go to step 1 unless we've imported and resolved everything

The order is such that all dependencies are resolved before a hook that asked
for dependencies is resolved.

The post_register also follows this where all dependencies are resolved before
a hook that asks for them.

Asking for all hooks in a namespace
-----------------------------------

You may specify a special ``("namespace", "__all__")``  dependency which will
make that hook depend on all hooks that haven't already been imported. Note that
this should be used sparingly as a hook that asks for it cannot be explicitly
asked for by another hook.
