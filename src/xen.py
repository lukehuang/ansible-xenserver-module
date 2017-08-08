""" The xen Ansible module for managing VMs.

See the DOCUMENTATION and EXAMPLES strings below for more information.


http://docs.ansible.com/ansible/latest/dev_guide/developing_modules.html

"""
from ansible.module_utils.basic import AnsibleModule


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
  image:
    description: Image name.
    required: true
"""  # must be valid YAML


EXAMPLES = """
- zen:
    execute: true
"""  # plain text


_ARGS_SPEC = {
    "image": {
        "type": "str", 
        "required": True
    }
}


def main():
    """ Execute the module.

    """
    module = AnsibleModule(_ARGS_SPEC, supports_check_mode=True)
    changed = False  # TODO: set to True if this will make changes
    if module.check_mode:
        # Determine whether or not this would have made any changes to the
        # target, but don't actually do anything.
        module.exit_json(changed=changed)  # calls exit(0)
    # TODO: Implement the module functionality.
    module.exit_json(changed=changed, **module.params)  # calls exit(0)


# Make the module executable.

if __name__ == "__main__":
    raise SystemExit(main())
