#!/usr/bin/env python3
"""Audit ownership/readiness of USB actions across device and common init."""
import argparse
import fnmatch
from pathlib import Path
import re

parser = argparse.ArgumentParser()
parser.add_argument("source", type=Path)
parser.add_argument("--ramdisk", type=Path)
args = parser.parse_args()
tree = Path(__file__).resolve().parents[1]
device_root = args.ramdisk or tree / "recovery/root"
device_text = (device_root / "init.recovery.usb.rc").read_text()
common_text = (args.source / "bootable/recovery/etc/init.rc").read_text()
if args.ramdisk:
    common_text = (args.ramdisk / "system/etc/init/hw/init.rc").read_text()

def actions(text):
    result = []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if raw.startswith("on "):
            current = (line[3:], [])
            result.append(current)
        elif not raw[0].isspace():
            current = None
        elif current:
            current[1].append(line)
    return result

dev = actions(device_text)
combined = actions(common_text) + dev
assert "setprop sys.usb.configfs 1" in dict(dev)["early-init"]
assert "setprop sys.usb.controller ${ro.boot.usbcontroller:-a600000.dwc3}" in dict(dev)["init"]
assert "on boot" not in device_text
assert "g2" not in device_text
assert "mount configfs" not in device_text
assert "mount functionfs adb " not in device_text
assert "mount functionfs fastboot " not in device_text
assert "mkdir /config/usb_gadget/g1 " not in device_text
assert "wait /sys/class/udc/${sys.usb.controller} 2" in dict(dev)["init"]
for function in ("adb", "fastboot", "mtp"):
    count = sum(command.startswith(f"mount functionfs {function} ")
                for _, commands in combined for command in commands)
    assert count == 1, f"{function} FunctionFS must have one owner, got {count}"

def triggered(condition, props):
    terms = condition.split(" && ")
    if not all(term.startswith("property:") for term in terms):
        return False
    for term in terms:
        name, value = term[len("property:"):].split("=", 1)
        if name not in props or not fnmatch.fnmatchcase(props[name], value):
            return False
    return True

cases = 0
for mode in ("adb", "sideload", "fastboot", "mtp", "mtp,adb"):
    for adb_ready in ("0", "1"):
        for mtp_ready in ("0", "1"):
            props = {"sys.usb.configfs": "1", "sys.usb.config": mode,
                     "sys.usb.ffs.ready": adb_ready, "sys.usb.ffs.mtp.ready": mtp_ready}
            commands = [command for condition, body in combined if triggered(condition, props)
                        for command in body]
            binds = [command for command in commands
                     if command.startswith("write /config/usb_gadget/g1/UDC ")]
            expected = ((mode in ("adb", "sideload", "fastboot") and adb_ready == "1") or
                        (mode == "mtp" and mtp_ready == "1") or
                        (mode == "mtp,adb" and adb_ready == mtp_ready == "1"))
            assert len(binds) == int(expected), (mode, adb_ready, mtp_ready, binds)
            assert all(command.endswith("${sys.usb.controller}") for command in binds)
            links = [command.split()[-1] for command in commands if command.startswith("symlink ")]
            assert len(links) == len(set(links)), f"Duplicate function links for {props}"
            cases += 1

props_text = (tree / "system.prop").read_text()
assert re.search(r"^ro.recovery.usb.vid=18D1$", props_text, re.M)
assert "write /config/usb_gadget/g1/idVendor" not in device_text
assert "0x${ro.recovery.usb.mtp.pid}" in device_text
assert "0x${ro.recovery.usb.mtpadb.pid}" in device_text
if args.ramdisk:
    packaged_props = (args.ramdisk / "prop.default").read_text()
    for key, value in (("vid", "18D1"), ("adb.pid", "D001"),
                       ("fastboot.pid", "4EE0"), ("mtp.pid", "4EE1"),
                       ("mtpadb.pid", "4EE2")):
        assert re.search(r"^ro.recovery.usb\." + re.escape(key) + "=" + value + "$",
                         packaged_props, re.M), f"Missing packaged USB ID: {key}"
assert not re.search(r"^\s*setprop sys.usb.config adb$",
                     (device_root / "init.recovery.qcom.rc").read_text(), re.M)
print(f"PASS: single FunctionFS owners and {cases} ADB/sideload/fastboot/MTP readiness cases")
