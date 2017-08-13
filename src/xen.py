""" The xen Ansible module for managing VMs.

See the DOCUMENTATION and EXAMPLES strings below for more information.

"""
# Ansible modules do not use the normal Python import machinery, so all imports
# must be absolute. Even then, there does not seem to be any way to import
# local libraries for sharing code within a project.
# <http://docs.ansible.com/ansible/latest/dev_guide/developing_modules.html>

from ansible.module_utils.basic import AnsibleModule
from contextlib import contextmanager
from XenAPI import Session


__all__ = "main",


ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": "preview",
    "supported_by": "committer",
}


DOCUMENTATION = """
module: xen 
short_description: manage Xen VMs
description: |
  Create, start, stop, suspend, and destroy VMs in a Xen pool.
requirements:
  - XenAPI (1.2+)
notes:
  - U(https://github.com/mdklatt/ansible-xenserver-module)
version_added: "2.2"
author: Michael Klatt
options:
  host:
    description: XenServer host URL.
    required: true
  username:
    description: XenServer root user.
    required: false
    default: root
  password:
    description: XenServer root password.
    required: true
  name:
    description: VM name label
    required: false
  tags:
    description: VM tag values
    required: false
  template:
    description: Template to create new VMs from.
    required: false
"""  # must be valid YAML


EXAMPLES = """
- zen:
    host: http://123.45.67.89
    username: root
    password: abc123
"""  # plain text


_ARGS = {
    "host": {
        "type": "str",
        "required": True
    },
    "username": {
        "type": "str",
        "default": "root",
    },
    "password": {
        "type": "str",
        "required": True,
        "no_log": True
    },
    "name": {
        "type": "list",
        "default": [],
    },
    "tags": {
        "type": "dict",
    },
    "state": {
        "type": "str",
        "choices": ["present", "absent", "running", "stopped", "restarted"],
        "default": "present",
    },
    "template": {
        "type": "str", 
    }
}


_MUTEX = [
    ["name", "tags"],
]


def main():
    """ Execute the module.

    """
    module = AnsibleModule(_ARGS, mutually_exclusive=_MUTEX,
                           supports_check_mode=True)
    if module.params["state"] == "present" and not module.params["template"]:
        module.fail_json(msg="'template' is required for state 'present'")
    with _connect(module.params) as xen:
        instances = xen.VM.get_all_records().values()
    changed = False  # TODO: set to True if this will make changes
    if module.check_mode:
        # Determine whether or not this would have made any changes to the
        # target, but don't actually do anything.
        module.exit_json(changed=changed)  # calls exit(0)
    module.exit_json(changed=changed, **module.params)  # calls exit(0)


@contextmanager
def _connect(params):
    """ Context manager for a XenAPI session.

    """
    # Even though all modules in this project need this function, it cannot be
    # put into a local library (see comments at top).
    session = Session(params["host"])
    username = params["username"]
    password = params["password"]
    session.login_with_password(username, password, "1.0", "ansible-xenserver")
    try:
        yield session.xenapi
    finally:
        session.xenapi.session.logout()
    return


# Make the module executable.

if __name__ == "__main__":
    raise SystemExit(main())
