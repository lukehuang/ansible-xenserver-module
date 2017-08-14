""" Test suite for the xen module.

The script can be executed on its own or incorporated into a larger test suite.
The ANSIBLE_LIBRARY environment variable must include src/, and pytest must be
run with `--ansible-host-pattern=localhost`.

"""
import pytest

# For normal unit testing, a mock XenServer host could be used to verify
# communication. However, the nature of Ansible makes this impossible. Ansible
# modules are run as external processes, so the interpreter instance running
# the tests has no access to the module code that must be monkey patched.
# <docs.ansible.com/ansible/latest/dev_guide/developing_program_flow_modules.html>


def test_params(ansible_module):
    """ Test module parameter passing.

    This verifies that the module can be successfully loaded by Ansible and
    called with all of its documented parameters.

    """
    # Module execution is expected to fail in the XenAPI library with an
    # IOError because there is no XenServer host to connect to. Make sure the
    # failure is because of this, which at least verifies that the module can
    # be least called with the expected parameters.
    params = {
        "host": "localhost",
        "username": "root",
        "password": "abc123",
        "name": "vm1",
        "state": "running",
    }
    result = ansible_module.xen(**params)
    traceback = result["localhost"]["exception"].rstrip()
    assert traceback.endswith("IOError: unsupported XML-RPC protocol")
    return


# Make the module executable.

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
