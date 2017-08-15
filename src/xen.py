""" The xen Ansible module for managing VMs.

Check mode is supported. Rapid power cycling may cause certain tasks to fail;
the `wait_for` module may be necessary to ensure that a VM has finished booting
up. See the DOCUMENTATION and EXAMPLES strings below for more information.

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
        "halted": _halted,
        "present": _present,
        "restarted": _restarted,
        "running": _running,
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
                changed = action(xen, record, async, check) or changed
            except RuntimeError as err:
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


def _async_wait(action):
    """ Decorator for waiting for pending VM operations to complete.

    """
    # This allows a single asynchronous action (the typical use case) to return
    # quickly to the playbook, but prevents a situation where follow-on actions
    # are out of phase with the pending VM state.
    #
    # If full asynchronous behavior is really needed, it might be possible for
    # each action to predict the pending VM state by inspecting the sequence of
    # operations in its queue.

    def wrapper(xen, record, *args, **kwargs):
        """ Wrapper function for calling action. """
        objref = record["object_ref"]
        while record["current_operations"]:
            # TODO: Probably need an `async_timeout` option here.
            # Wait for the operations queue to empty.
            record = xen.VM.get_record(objref)  # removes object_ref
            sleep(0.1)
        record.update({"object_ref": objref})  # action will need this
        return action(xen, record, *args, **kwargs)

    return wrapper


@_async_wait
def _halted(xen, record, async=False, check=False):
    """ Ensure that the VM is halted.

    Returns True if this requires modifying the VM state. In check mode the VM
    is not modified. The `async` option only applies to operations performed
    within a single action; multiple actions are always synchronous.

    """
    # TODO: All state functions are almost identical; refactor.
    actions = {
        # RPC needed to achieve the desired state.
        "halted": None,
        "running": "clean_shutdown",
        "suspended": "hard_shutdown"
    }
    state = record["power_state"].lower()
    try:
        rpc = actions[state]
    except KeyError:
        raise RuntimeError("VM is in unexpected state {:s}".format(state))
    if not rpc:  # VM is already in the desired state
        return False
    if not check:
        # Put VM in the desired state.
        if rpc not in record["allowed_operations"]:
            # This can occur while rapidly cycling power states, i.e. a clean
            # shutdown will be refused while the VM is still booting up. It
            # shouldn't be an issue during normal operations.
            raise RuntimeError("VM refuses {:s} at this time".format(rpc))
        task = getattr(xen.Async.VM, rpc)(record["object_ref"])
        while not async and xen.task.get_status(task) == "pending":
            # TODO: Probably need an `async_timeout` option here.
            # Wait for task to complete before returning.
            sleep(0.1)
        xen.task.destroy(task)
    return True


@_async_wait
def _present(xen, record, async=False, check=False):
    """ Ensure that the VM is present.

    Returns True if this requires modifying the VM state. In check mode the VM
    is not modified. The `async` option only applies to operations performed
    within a single action; multiple actions are always synchronous.

    """
    # TODO: Should this ensure that the VM is running or just that it exists?
    raise NotImplementedError


@_async_wait
def _restarted(xen, record, async=False, check=False):
    """ Ensure that the VM is started from a power off state.

    This always returns True because restarting always modifies the VM state.
    In check mode the VM is not modified. The `async` option only applies to
    operations performed within a single action; multiple actions are always
    synchronous.

    """
    # TODO: All state functions are almost identical; refactor.
    pause = force = False
    actions = {
        # FIXME: Use a delay or do a hard_reboot from suspended state?
        # Resuming from a suspended state might not be equivalent to a restart,
        # but attempting to reboot after resuming always fails because the VM
        # is not yet ready for clean_reboot.
        "halted": ("start", (pause, force)),
        "running": ("clean_reboot", tuple()),
        "suspended": ("resume", (pause, force)),
    }
    state = record["power_state"].lower()
    try:
        rpc, args = actions[state]
    except KeyError:
        raise RuntimeError("VM is in unexpected state {:s}".format(state))
    if not check:
        # Put VM in the desired state.
        if rpc not in record["allowed_operations"]:
            # This can occur while rapidly cycling power states, i.e. a
            # clean shutdown will be refused while the VM is still booting
            # up. It shouldn't be an issue during normal operations.
            raise RuntimeError("VM refuses {:s} at this time".format(rpc))
        task = getattr(xen.Async.VM, rpc)(record["object_ref"], *args)
        while not async and xen.task.get_status(task) == "pending":
            # TODO: Probably need an `async_timeout` option here.
            # Wait for task to complete before returning.
            sleep(0.1)
        xen.task.destroy(task)
    return True


@_async_wait
def _running(xen, record, async=False, check=False):
    """ Ensure that the VM is running.

    Returns True if this requires modifying the VM state. In check mode the VM
    is not modified. The `async` option only applies to operations performed
    within a single action; multiple actions are always synchronous.

    """
    # TODO: All state functions are almost identical; refactor.
    pause = force = False
    actions = {
        # RPC needed to achieve the desired state.
        "halted": "start",
        "running": None,
        "suspended": "resume",
    }
    state = record["power_state"].lower()
    try:
        rpc = actions[state]
    except KeyError:
        raise RuntimeError("VM is in unexpected state {:s}".format(state))
    if not rpc:  # VM is already in the desired state
        return False
    if not check:
        # Put VM in the desired state.
        if rpc not in record["allowed_operations"]:
            # This can occur while rapidly cycling power states, i.e. a clean
            # shutdown will be refused while the VM is still booting up. It
            # shouldn't be an issue during normal operations.
            raise RuntimeError("VM refuses {:s} at this time".format(rpc))
        task = getattr(xen.Async.VM, rpc)(record["object_ref"], pause, force)
        while not async and xen.task.get_status(task) == "pending":
            # TODO: Probably need an `async_timeout` option here.
            # Wait for task to complete before returning.
            sleep(0.1)
        xen.task.destroy(task)
    return True


# Make the module executable.

if __name__ == "__main__":
    raise SystemExit(main())
