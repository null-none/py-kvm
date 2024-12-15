import unix
import os
import json

from datetime import datetime
import weakref

from .exceptions import KvmError
from .image import Image

class Hypervisor:
    """This object represent an Hypervisor. **host** must be an object of
    type ``unix.Local`` or ``unix.Remote`` (or an object inheriting from
    them).
    """

    def _convert(self, value):
        value = value.strip()
        if value.isdigit():
            return int(value)
        for val, map_val in (("yes", True), ("no", False)):
            if value == val:
                return map_val
        return value

    def __init__(self, host, uri):
        # Controls.
        self._CONTROLS = {"parse": False, "ignore_opts": []}
        unix._CONTROLS.update(self._CONTROLS)

        self.__MAPFILE = os.path.join(os.path.dirname(__file__), "kvm.json")

        self._MAPPING = json.loads(
            "".join(
                [
                    line
                    for line in open(self.__MAPFILE).readlines()
                    if not line.startswith("#")
                ]
            )
        )

        self.uri = uri
        host.__class__.__init__(self)
        self.__dict__.update(host.__dict__)
        for control, value in self._CONTROLS.items():
            setattr(self, "_%s" % control, value)

    def virsh(self, command, *args, **kwargs):
        """Wrap the execution of the virsh command. It set a control for
        putting options after the virsh **command**. If **parse** control
        is activated, the value of ``stdout`` is returned or **KvmError**
        exception is raised.
        """
        if self._ignore_opts:
            for opt in self._ignore_opts:
                kwargs.update({opt: False})

        virsh_cmd = "virsh --connect %s" % (self.uri or "qemu:///session")
        with self.set_controls(options_place="after", decode="utf-8"):
            status, stdout, stderr = self.execute(virsh_cmd, command, *args, **kwargs)
            # Clean stdout and stderr.
            if stdout:
                stdout = stdout.rstrip("\n")
            if stderr:
                stderr = stderr.rstrip("\n")

            if not self._parse:
                return status, stdout, stderr
            elif not status:
                raise KvmError(stderr)
            else:
                stdout = stdout.splitlines()
                return stdout[:-1] if not stdout[-1] else stdout

    def list_domains(self, **kwargs):
        """List domains. **kwargs** can contains any option supported by the
        virsh command. It can also contains a **state** argument which is a
        list of states for filtering (*all* option is automatically set).
        For compatibility the options ``--table``, ``--name`` and ``--uuid``
        have been disabled.

        Virsh options are (some option may not work according your version):
            * *all*: list all domains
            * *inactive*: list only inactive domains
            * *persistent*: include persistent domains
            * *transient*: include transient domains
            * *autostart*: list autostarting domains
            * *no_autostart*: list not autostarting domains
            * *with_snapshot*: list domains having snapshots
            * *without_snapshort*: list domains not having snapshots
            * *managed_save*:  domains that have managed save state (only
                                possible if they are in the shut off state,
                                so you need to specify *inactive* or *all*
                                to actually list them) will instead show as
                                saved
            * *with_managed_save*: list domains having a managed save image
            * *without_managed_save*: list domains not having a managed
                                        save image
        """
        # Remove incompatible options between virsh versions.
        kwargs.pop("name", None)
        kwargs.pop("uuid", None)

        # Get states argument (which is not an option of the virsh command).
        states = kwargs.pop("states", [])
        if states:
            kwargs["all"] = True

        # Add virsh options for kwargs.
        virsh_opts = {arg: value for arg, value in kwargs.items() if value}

        # Get domains (filtered on state).
        domains = {}
        with self.set_controls(parse=True):
            stdout = self.virsh("list", **virsh_opts)

            for line in stdout[2:]:
                line = line.split()
                (domid, name, state), params = line[:3], line[3:]
                # Manage state in two words.
                if state == "shut":
                    state += " %s" % params.pop(0)
                domain = {"id": int(domid) if domid != "-" else -1, "state": state}
                if "title" in kwargs:
                    domain["title"] = " ".join(params) if params else ""
                domains[name] = domain

        return domains

    def list_networks(self, **kwargs):
        with self.set_controls(parse=True):
            stdout = self.virsh("net-list", **kwargs)
            networks = {}
            for line in stdout[2:]:
                line = line.split()
                name, state, autostart = line[:3]
                net = dict(state=state, autostart=self._convert(autostart))
                if len(line) == 4:
                    net.update(persistent=self._convert(line[3]))
                networks.setdefault(name, net)
        return networks

    def list_interfaces(self, **kwargs):
        with self.set_controls(parse=True):
            stdout = self.virsh("iface-list", **kwargs)
            return {
                name: {"state": state, "mac": mac}
                for line in self.virsh("iface-list", **kwargs)[2:]
                for name, state, mac in [line.split()]
            }

    def list_pools(self, **kwargs):
        with self.set_controls(parse=True):
            stdout = self.virsh("pool-list", **kwargs)
            pools = {}
            for line in stdout[2:]:
                line = line.split()
                name, state, autostart = line[:3]
                pool = dict(state=state, autostart=self._convert(autostart))
                if len(line) > 3:
                    pool.update(
                        persistent=self._convert(line[3]),
                        capacity=" ".join(line[4:6]),
                        allocation=" ".join(line[6:8]),
                        available=" ".join(line[8:10]),
                    )
                pools.setdefault(line[0], pool)
            return pools

    def list_volumes(self, pool, **kwargs):
        with self.set_controls(parse=True):
            stdout = self.virsh("vol-list", pool, **kwargs)
            volumes = {}
            for line in stdout[2:]:
                line = line.split()
                name, path = line[:2]
                volume = dict(path=path)
                if len(line) > 2:
                    volume.update(
                        type=line[2],
                        capacity=" ".join(line[3:5]),
                        allocation=" ".join(line[5:7]),
                    )
                volumes.setdefault(name, volume)
            return volumes

    def list_secrets(self, **kwargs):
        with self.set_controls(parse=True):
            stdout = self.virsh("secret-list", **kwargs)
            secrets = {}
            for line in stdout[2:]:
                line = line.split()
                uuid, usage = line[0], line[1:]
                secrets.setdefault(uuid, " ".join(usage))
            return secrets

    def list_snapshots(self, domain, **kwargs):
        kwargs.pop("tree", None)
        kwargs.pop("name", None)
        with self.set_controls(parse=True):
            stdout = self.virsh("snapshot-list", domain, **kwargs)
            snapshots = {}
            for line in stdout[2:]:
                line = line.split()
                creation_date = datetime.strptime(
                    " ".join(line[1:4]), "%Y-%m-%d %H:%M:%S %z"
                )
                state = line[4]
                if state == "shut":
                    state += line[5]
                    parent = line[6] if "parent" in kwargs else None
                else:
                    parent = line[5] if "parent" in kwargs else None
                snapshot = {"creation_date": creation_date, "state": state}
                if parent and parent != "null":
                    snapshot.update(parent=parent)
                snapshots.setdefault(line[0], snapshot)
            return snapshots

    @property
    def image(self):
        return Image(weakref.ref(self)())
