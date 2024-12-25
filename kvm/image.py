class _Image(object):
    def __init__(self, host):
        self._host = host

    def check(self, path, **kwargs):
        return self._host.execute("qemu-img check", path, **kwargs)

    def create(self, path, size, **kwargs):
        return self._host.execute("qemu-img create", path, size, **kwargs)

    def commit(self, path, **kwargs):
        return self._host.execute("qemu-img commit", path, **kwargs)

    def compare(self, *paths, **kwargs):
        return self._host.execute("qemu-img compare", *paths, **kwargs)

    def convert(self, src_path, dst_path, **kwargs):
        with self._host.set_controls(options_place="after"):
            return self._host.execute("qemu-img convert", src_path, dst_path, **kwargs)

    def info(self, path, **kwargs):
        status, stdout, stderr = self._host.execute("qemu-img info", path, **kwargs)
        if not status:
            raise OSError(stderr)
        return _dict(stdout.splitlines())

    def map(self, path, **kwargs):
        return self._host.execute("qemu-img map", path, **kwargs)

    def snapshot(self, path, **kwargs):
        return self._host.execute("qemu-img snapshot", path, **kwargs)

    def rebase(self, path, **kwargs):
        return self._host.execute("qemu-img rebase", path, **kwargs)

    def resize(self, path, size):
        return self._host.execute("qemu-img resize", path, size)

    def amend(self, path, **kwargs):
        return self._host.execute("qemu-img amend", path, **kwargs)

    def load(self, path, device="nbd0", **kwargs):
        kwargs["c"] = "/dev/%s" % device
        kwargs["d"] = False
        return self._host.execute("qemu-nbd", path, **kwargs)

    def unload(self, device="nbd0", **kwargs):
        kwargs["c"] = False
        kwargs["d"] = "/dev/%s" % device
        return self._host.execute("qemu-nbd", **kwargs)
