""" The xen Ansible module for managing VMs.

Check mode is supported. Attempting to shut down a VM while it is booting up
will fail, so avoid rapid cycling of power states. See the DOCUMENTATION and
EXAMPLES strings below for more information.

"""
# Ansible modules do not use the normal Python import machinery, so all imports
# must be absolute. Even then, there does not seem to be any way to import
# local libraries for sharing code within a project.
# <http://docs.ansible.com/ansible/latest/dev_guide/developing_modules.html>

from ansible.module_utils.basic import AnsibleModule
from contextlib import contextmanager
from time import sleep
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
    description: Match VMs by name label(s).
    required: false
  tags:
    description: Match VMs by tag value(s).
    required: false
  state:
    description: Desired VM state.
  template:
    description: Template to create new VMs from.
    required: false
  aysnc:
    description: Perform operations asynchronously if possible.
    default: false
"""  # must be valid YAML


EXAMPLES = """
- zen:
    host: http://123.45.67.89
    username: root
    password: abc123
    name: vm01
    template: Centos 7.3.1611
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
    },
    "tags": {
        "type": "list",
    },
    "state": {
        "type": "str",
        "choices": ["present", "absent", "running", "halted", "restarted"],
        "default": "present",
    },
    "template": {
        "type": "str", 
    },
    "async": {
        "type": "bool",
        "default": False,
    }
}


def main():
    """ Execute the module.

    WARNING: Rapidly cycling through states in async mode may not have the
    desired effect because the VM appears to get out of sync with its reported
    power state.

    """
    module = AnsibleModule(
        _ARGS,
        required_one_of=[["name", "tags"]],  # TODO: refactor
        mutually_exclusive=[["name", "tags"]],
        required_if=[("state", "present", ["template"])],
        supports_check_mode=True
    )
    if module.params["state"] == "present" and not module.params["template"]:
        module.fail_json(msg="'template' is required for state 'present'")
    filters = {"is_a_template": [False]}
    if "name" in module.params:
        filters["name_label"] = module.params["name"]
    else:
        filters["tags"] = module.params["tags"]
    actions = {
        "running": _start,
        "halted": _shutdown,
    }
    action = actions[module.params["state"]]
    async = module.params["async"]
    check = module.check_mode
    with _connect(module.params) as xen:
        module.log("connected to {:s}".format(module.params["host"]))
        records = list(_xeniter(xen, filters))
        changed = False
        for record in records:
            try:
                changed = action(xen, record, check, async) or changed
            except (AssertionError, RuntimeError) as err:
                module.fail_json(msg=err.message, instance=record)
    module.exit_json(changed=changed, instances=records)  # calls exit(0)


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


def _xeniter(xen, filters):
    """ Iterate over filtered inventory records from the host.

    """
    output = ("object_ref", "uuid", "name_label", "name_description", "tags",
              "power_state", "current_operations", "allowed_operations")
    for objref, record in xen.VM.get_all_records().iteritems():
        record.update({"object_ref": objref})
        valid = True
        for key, matches in filters.iteritems():
            # Apply filters.
            if key == "tags":
                # TODO: Handle other fields with multiple values.
                valid = all(value in record.get(key) for value in matches)
            else:
                valid = record.get(key) in matches
            if not valid:
                break
        if valid:
            # Don't remove unwanted fields until the last minute so that
            # filtering can be applied to any field.
            record = {key: record[key] for key in output}
            yield record
    return


def _start(xen, record, check=False, async=False):
    """ Ensure that the VM is started.

    Returns True if starting the VM will modify its state. In check mode the
    VM is not modified.

    The `async` option only applies to operations performed by this action. If
    the VM operations queue is not empty, this will block until it is. This is
    done to avoid putting the VM into a contradictory state.

    """
    # TODO: This is almost identical to _shutdown; refactor.
    objref = record["object_ref"]
    while record["current_operations"]:
        # The VM is already in the middle of one or more asynchronous
        # operations, so wait until its state is finalized to avoid dueling
        # state changes.
        sleep(0.5)  # don't DOS the server
        record = xen.VM.get_record(objref)
    pause = force = False
    actions = {"halted": "start", "suspended": "resume"}
    state = record["power_state"].lower()
    try:
        action = actions[state]
    except KeyError:
        assert state == "running"
        return False
    if not check:
        # VM needs to be modified to achieve the desired state.
        #assert action in record["allowed_operations"]
        api = xen.Async.VM if async else xen.VM
        getattr(api, action)(objref, pause, force)
    return True


def _shutdown(xen, record, check=False, async=False):
    """ Ensure that the VM is shut down.

    Returns True if shutting down the VM will modify its state. In check mode
    the VM is not actually modified.

    The `async` option only applies to operations performed by this action. If
    the VM operations queue is not empty, this will block until it is. This is
    done to avoid putting the VM into a contradictory state.

    """
    # TODO: This is almost identical to _start; refactor.
    objref = record["object_ref"]
    while record["current_operations"]:
        # The VM is already in the middle of one or more asynchronous
        # operations, so wait until its state is finalized to avoid dueling
        # state changes.
        sleep(0.5)  # don't DOS the server
        record = xen.VM.get_record(objref)
    actions = {"running": "clean_shutdown", "suspended": "hard_shutdown"}
    state = record["power_state"].lower()
    try:
        action = actions[state]
    except KeyError:
        assert state == "halted"
        return False
    if not check:
        # VM needs to be modified to achieve the desired state.
        if action not in record["allowed_operations"]:
            # An expected cause of this is requesting clean_shutdown while the
            # VM is booting up. This has been observed while rapidly cycling
            # power states during testing, but shouldn't be an issue during
            # normal operations.
            raise RuntimeError("VM refuses {:s} at this time".format(action))
        api = xen.Async.VM if async else xen.VM
        getattr(api, action)(record["object_ref"])
    return True


# Make the module executable.

if __name__ == "__main__":
    raise SystemExit(main())
