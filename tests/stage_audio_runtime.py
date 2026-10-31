#!/usr/bin/env python3
"""Reproduce the device-matched audio assets from an extracted FroggerPro OTA.

Copies stock assets only; never patches ELF files or copies kernel modules.
"""
import argparse
from pathlib import Path
import re
import shutil
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("dump", type=Path)
args = parser.parse_args()
dump = args.dump.resolve()
root = Path(__file__).resolve().parents[1] / "recovery/root"
search = [dump / p for p in ("vendor/lib64", "system/system/lib64", "system_ext/lib64", "odm/lib64")]
shared = root / "vendor/aera-audio-lib64"
shared.mkdir(parents=True, exist_ok=True)
seeds = [dump / "vendor" / p for p in (
    "bin/pd-mapper", "bin/dspservice", "bin/adsprpcd", "bin/audioadsprpcd",
    "lib64/libagmipcservice.so", "lib64/libpalipcservice.so", "lib64/libpalclient.so",
    "lib64/libpaleventnotifier.so", "lib64/libagmmixer.so", "lib64/libtinyalsa.so",
    # TinyALSA/AGM open these by name; DT_NEEDED traversal misses them.
    "lib64/libsndcardparser.so", "lib64/libagm_pcm_plugin.so",
    "lib64/libagm_mixer_plugin.so", "lib64/libagm_compress_plugin.so",
)]
# Keep these on recovery's matching Bionic/linker. libdl_android is already
# supplied by common recovery; vendor/private C++ dependencies stay isolated.
platform = {"libc.so", "libdl.so", "libm.so", "libdl_android.so"}
# Stock's Binder NDK is a system library. Pair it with the same system Binder,
# not the older vendor VNDK copy (which lacks accessor/transport exports).
preferred = {"libbinder.so": dump / "system/system/lib64/libbinder.so"}
queue = list(seeds)
seen = set()
providers = {}
while queue:
    path = queue.pop()
    if path in seen:
        continue
    assert path.is_file(), f"Missing stock audio asset: {path}"
    seen.add(path)
    result = subprocess.run(["readelf", "-d", str(path)], capture_output=True, text=True, check=True)
    for name in re.findall(r"Shared library: \[(.*?)\]", result.stdout):
        if name in platform:
            continue
        candidate = preferred.get(name) or next(
            (directory / name for directory in search if (directory / name).is_file()), None)
        assert candidate, f"Unresolved stock dependency: {path.name} -> {name}"
        queue.append(candidate)
    if path.parent.name == "bin":
        target = root / "vendor/bin" / ("aera-" + path.name)
    else:
        assert path.name not in providers or providers[path.name] == path
        providers[path.name] = path
        target = shared / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)

def copy(source, destination):
    target = root / destination
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dump / source, target)

for name in ("card-defs.xml", "usecaseKvManager.xml", "mem_logger_config.xml"):
    copy("vendor/etc/" + name, "vendor/etc/" + name)
for subtree in ("audio/sku_kera", "acdbdata/kera_qrd"):
    shutil.copytree(dump / "vendor/etc" / subtree, root / "vendor/etc" / subtree, dirs_exist_ok=True)
for stem in ("mixer_paths", "resourcemanager"):
    source = f"vendor/etc/audio/sku_kera/{stem}_kera_qrd.xml"
    copy(source, f"vendor/etc/{stem}_kera_qrd.xml")
    copy(source, f"vendor/etc/{stem}.xml")
copy("vendor/etc/seccomp_policy/vendor.qti.hardware.dsp.policy",
     "vendor/etc/seccomp_policy/vendor.qti.hardware.dsp.policy")
copy("vendor/firmware/aw882xx_acf.bin", "vendor/firmware/aw882xx_acf.bin")
print(f"Staged {len(seen)} stock audio ELFs ({sum(p.stat().st_size for p in seen) / 1048576:.1f} MiB) and Kera calibration/configuration")
