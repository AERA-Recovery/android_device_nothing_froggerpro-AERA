#!/usr/bin/env python3
"""Offline packaging/ELF audit, not an on-device audio playback test."""
import argparse
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("ramdisk", type=Path)
args = parser.parse_args()
root = args.ramdisk.resolve()
search = [root / p for p in (
    "vendor/aera-audio-lib64", "vendor/lib64", "system/lib64",
    "system/lib64/bootstrap", "system_ext/lib64",
)]
queue = [root / "vendor/bin" / name for name in (
    "aera-pd-mapper", "aera-dspservice", "aera-adsprpcd", "aera-audioadsprpcd",
)] + [root / "system/bin" / name for name in (
    "aera-audio-service", "aera-audio-bridge",
)] + list(search[0].glob("*.so"))
assert len(queue) > 5, "Audio runtime was not packaged"
for name in ("libsndcardparser.so", "libagm_pcm_plugin.so",
             "libagm_mixer_plugin.so", "libagm_compress_plugin.so"):
    assert (search[0] / name).is_file(), f"Missing dynamically loaded AGM plugin: {name}"
visited = set()
while queue:
    path = queue.pop()
    if path in visited:
        continue
    assert path.is_file(), f"Missing audio ELF: {path}"
    visited.add(path)
    dynamic = subprocess.check_output(["readelf", "-d", str(path)], text=True)
    for name in re.findall(r"Shared library: \[(.*?)\]", dynamic):
        target = next((d / name for d in search if (d / name).is_file()), None)
        assert target, f"Unresolved audio dependency: {path.name} -> {name}"
        queue.append(target)

provided = set()
required = {}
exports = {}
for path in visited | {root / "system/bin/linker64"}:
    symbols = subprocess.check_output(["readelf", "--dyn-syms", "--wide", str(path)], text=True)
    exports[path.name] = set()
    for binding, section, name in re.findall(
            r"\b(GLOBAL|WEAK)\s+(?:DEFAULT|PROTECTED|HIDDEN)\s+(\S+)\s+(\S+)", symbols):
        name = name.split("@")[0]
        if section != "UND":
            provided.add(name)
            exports[path.name].add(name)
        elif binding == "GLOBAL":
            required.setdefault(path.name, set()).add(name)
unresolved = {name: sorted(names - provided) for name, names in required.items() if names - provided}
assert not unresolved, f"Unresolved audio strong symbols: {unresolved}"
for name in ("libagmipcservice.so", "libpalipcservice.so"):
    assert "registerService" in exports[name], f"Missing service entry point in {name}"
for name in ("pal_init", "pal_stream_open", "pal_stream_start", "pal_stream_write",
             "pal_stream_stop", "pal_stream_close", "pal_stream_set_volume"):
    assert name in exports["libar-pal.so"], f"Missing PAL entry point: {name}"

for name in ("vendor/etc/mixer_paths.xml", "vendor/etc/resourcemanager.xml",
             "vendor/etc/card-defs.xml", "vendor/firmware/aw882xx_acf.bin",
             "vendor/etc/seccomp_policy/vendor.qti.hardware.dsp.policy"):
    assert (root / name).is_file(), f"Missing speaker/DSP asset: {name}"
assert list((root / "vendor/etc/acdbdata/kera_qrd").glob("*.acdb"))
qcom = (root / "init.recovery.qcom.rc").read_text()
assert "boot_adsp/boot" not in qcom and "remoteproc1/state" not in qcom
post_fs = qcom.split("on post-fs\n", 1)[1].split("\non ", 1)[0]
assert "start aera-pd-mapper" in post_fs
assert "mount ext4 /dev/block/by-name/dsp${ro.boot.slot_suffix} /vendor/dsp ro noload" in qcom
assert "sys.aera.audio.ready 0" in qcom
assert "start aera-adsp-ready" in qcom
bootstrap = (root / "system/bin/aera-audio-bootstrap").read_text()
assert "sys.aera.audio.ready" in bootstrap and "count" in bootstrap
assert "/mnt/aera-stock" not in bootstrap
assert '--early-adsp' in bootstrap
assert '/vendor/firmware_mnt/image/adsp.mdt' in bootstrap
assert 'ADSP is not running' in bootstrap
assert (root / "system/bin/aera-audio-bootstrap").stat().st_mode & 0o111
print(f"PASS: {len(visited)} audio dependency ELFs, strong symbols, PAL entry points, configuration and init wiring")
