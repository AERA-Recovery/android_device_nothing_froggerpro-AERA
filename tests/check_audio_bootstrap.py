#!/usr/bin/env python3
"""Exercise bootstrap ordering with fixtures, without touching a real device."""
from pathlib import Path
import subprocess
import tempfile

source = (Path(__file__).resolve().parents[1] /
          "recovery/root/system/bin/aera-audio-bootstrap").read_text()

for mode in ("missing-transport", "missing-fastrpc", "missing-runtime", "secure-only", "runtime-restored", "early-adsp"):
    with tempfile.TemporaryDirectory(prefix="froggerpro-bootstrap-", dir="/tmp") as directory:
        root = Path(directory)

        def write(relative, text):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            return path

        def shim(name, body):
            path = write("bin/" + name, "#!/bin/bash\n" + body + "\n")
            path.chmod(0o755)

        shim("getprop", f'''case "$1" in
ro.product.device) echo froggerpro;;
init.svc.aera-pd-mapper|init.svc.aera-dspservice) echo running;;
init.svc.*) [ -f '{root}/started' ] && grep -qx "${{1#init.svc.}}" '{root}/started' && echo running;;
sys.aera.audio.ready) [ -f '{root}/started' ] && grep -qx aera-agm-service '{root}/started' && echo 1;;
esac''')
        shim("setprop", f'''[ "$1" != ctl.start ] || echo "$2" >> '{root}/started' ''')
        shim("sleep", "exit 0")
        shim("mount", "exit 1")
        write("sys/class/remoteproc/remoteproc17/name", "3000000.remoteproc-adsp")
        write("sys/class/remoteproc/remoteproc17/state", "running")
        write("vendor/firmware_mnt/image/adsp.mdt", "firmware fixture")
        write("dev/snd/controlC0", "ALSA card fixture")
        write("dev/kmsg", "")
        (root / "tmp").mkdir()
        if mode in ("secure-only", "runtime-restored", "missing-runtime", "missing-fastrpc"):
            # Existing harmless character devices, never opened by bootstrap.
            (root / "dev/aud_pasthru_adsp").symlink_to("/dev/null")
        if mode in ("secure-only", "runtime-restored", "missing-runtime"):
            (root / "dev/fastrpc-adsp-secure").symlink_to("/dev/null")
        runtime_files = ("vendor/bin/aera-adsprpcd", "vendor/bin/aera-audioadsprpcd",
                         "vendor/aera-audio-lib64/libadsprpc.so")
        if mode == "secure-only":
            for name in runtime_files:
                write(name, "matched runtime fixture")
        if mode == "runtime-restored":
            shim("sleep", "mkdir -p '" + str(root / "vendor/bin") + "' '" +
                 str(root / "vendor/aera-audio-lib64") + "'\n" +
                 "touch " + " ".join("'" + str(root / name) + "'" for name in runtime_files))

        script = source.replace("PATH=/system/bin:/sbin", "PATH=@@BIN@@:/usr/bin:/bin")
        for prefix in ("/vendor/", "/sys/", "/proc/", "/dev/", "/tmp/", "/data/"):
            script = script.replace(prefix, "@@ROOT@@" + prefix)
        script = script.replace("@@ROOT@@", str(root)).replace("@@BIN@@", str(root / "bin"))
        target = write("bootstrap", script)
        args = ["bash", str(target)] + (["--early-adsp"] if mode == "early-adsp" else [])
        result = subprocess.run(args, capture_output=True, text=True, timeout=10)
        started = (root / "started").read_text().splitlines() if (root / "started").exists() else []
        if mode == "missing-transport":
            assert result.returncode == 1 and "ADSP audio packet transport is missing" in result.stderr
            assert not started, started
        elif mode == "missing-fastrpc":
            assert result.returncode == 1 and "ADSP FastRPC device is missing" in result.stderr
            assert not started, started
        elif mode == "missing-runtime":
            assert result.returncode == 1 and "ramdisk audio runtime is unavailable" in result.stderr
            assert not started, started
        elif mode in ("secure-only", "runtime-restored"):
            assert result.returncode == 0, result.stderr
            assert started == ["aera-adsprpcd", "aera-audioadsprpcd", "aera-agm-service"], started
        else:
            assert result.returncode == 0 and not started, (result.stderr, started)

print("PASS: missing transports/runtime block AGM; secure-only ADSP and restored runtime start both listeners before AGM; early ADSP stays independent")
