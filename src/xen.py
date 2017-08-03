""" The xen Ansible module.

See the DOCUMENTATION and EXAMPLES strings below for more information.

"""
from ansible.module_utils.basic import AnsibleModule


__all__ = "main",


__version__ = "0.1.0.dev0"  # PEP 0440 with Semantic Versioning


DOCUMENTATION = """
module: xen 
short_description: The xen module.
notes:
version_added: "2.2"
author: Michael Klatt
options:
  changed:
    description: Example of boolean option.
    required: false
    default: true
"""  # must be valid YAML


EXAMPLES = """
- "0.1.0.dev0":
    execute: true
"""  # plain text


_ARGS_SPEC = {
    # MUST use list for choices.
    "execute": {
        "required": False,
        "default": False,
        "type": "bool"
    }
}


def main():
    """ Execute the module.

    """
    module = AnsibleModule(_ARGS_SPEC, supports_check_mode=True)
    execute = module.params["execute"]
    if module.check_mode:
        # Determine whether or not this would have made any changes to the
        # target, but don't actually do anything.
        module.exit_json(changed=execute, rc=0)  # calls exit(0)
    # TODO: Implement the module functionality.
    module.exit_json(changed=execute, rc=0, **module.params)  # calls exit(0)


# Make the module executable.

if __name__ == "__main__":
    raise SystemExit(main())
