===
xen
===

.. |travis.png| image:: https://travis-ci.org/mdklatt/ansible-xen-module.png?branch=master
   :alt: Travis CI build status
   :target: `travis`_
.. _travis: https://travis-ci.org/mdklatt/ansible-xen-module
.. _Ansible: http://docs.ansible.com/ansible

|travis.png|

This is an `Ansible`_ module for managing XenServer assets.


Installation
============

Ansible searches for for modules specified by the ``ANSIBLE_LIBRARY``
environment variable or the ``library`` paramater in an ``ansible.cfg`` file.

The module can also be distributed with a role by placing it in the role's
``library`` directory. The module will be available to that role and any role
called afterwards.


Testing
=======

.. code-block:: console

    $ export ANSIBLE_LIBRARY=lib
    $ pytest --ansible-host-pattern=localhost test/
