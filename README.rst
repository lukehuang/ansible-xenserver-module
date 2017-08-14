=========
xenserver
=========

.. |travis.png| image:: https://travis-ci.org/mdklatt/ansible-xen-module.png?branch=master
   :alt: Travis CI build status
   :target: `travis`_
.. _travis: https://travis-ci.org/mdklatt/ansible-xen-module
.. _Ansible: http://docs.ansible.com/ansible

|travis.png|

This package contains `Ansible`_ modules for managing XenServer assets. Check
mode is supported.

The `xen` module is currently limited to starting and stopping VMs.


Installation
============

Ansible searches for for modules specified by the ``ANSIBLE_LIBRARY``
environment variable or the ``library`` parameter in an ``ansible.cfg`` file.

The module can also be distributed with a role by placing it in the role's
``library`` directory. The module will be available to that role and any role
called afterwards.


Testing
=======

.. code-block:: console

    $ export ANSIBLE_LIBRARY=src
    $ pytest --ansible-host-pattern=localhost test/
