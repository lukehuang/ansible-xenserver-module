""" Test suite for the xen module.

The script can be executed on its own or incorporated into a larger test suite.
The ANSIBLE_LIBRARY environment variable must include src/, and pytest must be
run with `--ansible-host-pattern=localhost`.

"""
import pytest


@pytest.mark.parametrize("execute", [True, False])
def test_xen(ansible_module, execute):
    """ Test the xen module.
    
    """
    params = {
        "execute": execute,
    }
    result = ansible_module.xen(**params)
    host = result["localhost"]
    assert not host.get("failed", False)
    assert host["changed"] == execute
    assert host["execute"] == execute
    return


# Make the module executable.

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
