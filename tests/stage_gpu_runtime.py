#!/usr/bin/env python3
"""Stage one matched Adreno vendor runtime, including dlopen-only helpers."""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import json

parser = argparse.ArgumentParser()
parser.add_argument('dump', type=Path)
args = parser.parse_args()
vendor_root = args.dump.resolve() / 'vendor'
vendor = vendor_root / 'lib64'
output = Path(__file__).resolve().parents[1] / 'recovery/root/vendor'
root = output / 'lib64'
# These are recovery's platform ABI; do not replace crypto/Binder/platform
# libraries globally with another ROM's copies. The packaged ELF audit checks
# the actual recovery providers after building.
platform = {
    'libc.so', 'libdl.so', 'libm.so', 'libdl_android.so', 'libc++.so',
    'libbase.so', 'libbinder.so', 'libbinder_ndk.so', 'libcutils.so',
    'libhardware.so', 'libhidlbase.so', 'liblog.so', 'libnativewindow.so',
    'libsync.so', 'libui.so', 'libutils.so', 'libvndksupport.so', 'libz.so',
    'libion.so', 'libdmabufheap.so',
}
queue = list((vendor / 'egl').glob('*.so')) + [vendor / n for n in (
    'hw/gralloc.default.so', 'libadreno_app_profiles.so',
    'libcamxexternalformatutils.so', 'libllvm-qgl.so',
    'hw/mapper.qti.so',
    'hw/android.hardware.graphics.mapper@4.0-impl-qti-display.so',
    'vendor.qti.hardware.display.snapalloc-impl.so',
)] + [vendor_root / 'bin/hw/vendor.qti.hardware.display.allocator-service']
seen = set()
while queue:
    path = queue.pop()
    if path in seen:
        continue
    assert path.is_file(), f'Missing GPU asset: {path}'
    seen.add(path)
    dest = output / path.relative_to(vendor_root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    dynamic = subprocess.check_output(['readelf', '-d', str(path)], text=True)
    for name in re.findall(r'Shared library: \[(.*?)\]', dynamic):
        if name in platform:
            continue
        dep = next((d / name for d in (vendor, vendor / 'egl') if (d / name).is_file()), None)
        if dep:
            queue.append(dep)
# Both the root dlopen search and the egl subdirectory must resolve the same
# driver, rather than leaving a stale second copy in the general library path.
shutil.copy2(vendor / 'egl/libEGL_adreno.so', root / 'libEGL_adreno.so')
# Android's recovery linker has no separate sphal namespace. Supply the mapper
# in its normal HAL location and in the general dlopen search path.
shutil.copy2(vendor / 'hw/mapper.qti.so', root / 'mapper.qti.so')
manifest = output / 'etc/vintf/manifest'
manifest.mkdir(parents=True, exist_ok=True)
for name in ('mapper.qti.xml', 'vendor.qti.hardware.display.allocator-service.xml'):
    shutil.copy2(vendor_root / 'etc/vintf/manifest' / name, manifest / name)
# SnapAlloc caches its format/constraint tables when the allocator starts,
# before recovery temporarily mounts the installed vendor for inspection.
# Missing JSON leaves even RGBA_8888 unrecognized despite successful EGL init.
display = output / 'etc/display'
display.mkdir(parents=True, exist_ok=True)
configs = [vendor_root / 'etc/display/formats.json'] + sorted(
    (vendor_root / 'etc/display').glob('*_alignments.json'))
for path in configs:
    json.loads(path.read_text())
    shutil.copy2(path, display / path.name)
print(f'Staged {len(seen)} GPU/allocator ELFs, mapper aliases, VINTF and {len(configs)} SnapAlloc tables')
