""" Test suite for the xen module.

The script can be executed on its own or incorporated into a larger test suite.
The ANSIBLE_LIBRARY environment variable must include src/, and pytest must be
run with `--ansible-host-pattern=localhost`.

"""
import pytest


def test_params(ansible_module):
    """ Test module parameter passing.
    
    """
    params = {
        "image": "CentOS 7",
    }
    result = ansible_module.xen(**params)
    host = result["localhost"]
    assert not host.get("failed", False)
    assert host["image"] == params["image"]
    return


# Make the module executable.

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
