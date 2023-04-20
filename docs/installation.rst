Installation
------------

Through pip
===========

The easiest way to install Soil is through pip, with Python >= 3.8:

.. code:: bash

   pip install soil


Now test that it worked by running the command line tool

.. code:: bash

   soil --help

   #or

   python -m soil --help

Or, if you're using using soil programmatically:

.. code:: python

   import soil
   print(soil.__version__)



Web UI
======

Soil also includes a web server that allows you to upload your simulations, change parameters, and visualize the results, including a timeline of the network.
To make it work, you have to install soil like this:

.. code::

  pip install soil[web]

Once installed, the soil web UI can be run in two ways:

.. code::

  soil-web

  # OR

  python -m soil.web


Development
===========

The latest version can be downloaded from `GitHub <https://github.com/gsi-upm/soil>`_ and installed manually:

.. code:: bash

   git clone https://github.com/gsi-upm/soil
   cd soil
   python -m venv .venv
   source .venv/bin/activate
   pip install --editable .