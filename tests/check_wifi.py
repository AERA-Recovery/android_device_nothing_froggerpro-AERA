#!/usr/bin/env python3
"""Audit the tree against an extracted stock OTA; does not access a device."""
import argparse
import pathlib
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("dump", type=pathlib.Path)
args = parser.parse_args()
tree = pathlib.Path(__file__).resolve().parents[1]
dump = args.dump.resolve()
config = (tree / "aera_config.mk").read_text()
board = (tree / "BoardConfig.mk").read_text()
product = (tree / "aera_froggerpro.mk").read_text()
assert "include $(DEVICE_PATH)/aera.mk" in board
assert "include $(DEVICE_PATH)/aera_config.mk" in board
assert "$(call inherit-product, $(DEVICE_PATH)/aera" not in product
assert re.search(r"^AERA_ENABLE_WLAN\s*:=\s*1$", (tree / "aera.mk").read_text(), re.M)

def modules(flag):
    match = re.search(r"^" + flag + r'\s*:=\s*"([^"]+)"', config, re.M)
    assert match, f"Missing {flag}"
    return match[1].split()

def canonical(name):
    return pathlib.Path(name).stem.replace("-", "_")

early = modules("AERA_LOAD_VENDOR_MODULES")
deferred = modules("AERA_POST_DECRYPT_MODULES")
installed = {}
for directory in ("system_dlkm", "vendor_dlkm"):
    for path in (dump / directory / "lib/modules").rglob("*.ko"):
        installed[canonical(path.name)] = path
all_modules = dict(installed)
for path in (dump / "vendor_boot/ramdisk/lib/modules").rglob("*.ko"):
    all_modules.setdefault(canonical(path.name), path)

def dependencies(path):
    value = subprocess.check_output(["modinfo", "-F", "depends", str(path)], text=True).strip()
    return [name.replace("-", "_") for name in value.split(",") if name]

early_loaded = set()
def load_early(name):
    name = canonical(name)
    if name in early_loaded:
        return
    early_loaded.add(name)
    if name in all_modules:
        for dependency in dependencies(all_modules[name]):
            load_early(dependency + ".ko")
for name in early:
    load_early(name)

ready = set(early_loaded)
for name in deferred:
    key = canonical(name)
    assert key in installed, f"{name} is missing from the installed system/vendor_dlkm"
    for dependency in dependencies(installed[key]):
        # Missing .ko files are kernel built-ins. Any loadable dependency must
        # already be in the early closure or precede this module in the list.
        assert dependency not in all_modules or dependency in ready, \
            f"{name} needs {dependency}.ko before it"
    ready.add(key)
assert "qca_cld3_qca6750" in ready and "icnss2" in ready
assert not any("peach" in name for name in deferred)

root = tree / "recovery/root"
wifi = (root / "init.recovery.wifi.rc").read_text()
assert "import /init.recovery.wifi.rc" in (root / "init.recovery.qcom.rc").read_text()
assert "/sys/kernel/icnss/wpss_boot 1" in wifi and "cnss-peach" not in wifi
assert "on property:twrp.modules.loaded=true" in wifi
for name in deferred:
    assert f"insmod /tmp/post_decrypt_modules/{name}" in wifi
assert wifi.index("/rfkill.ko") < wifi.index("/cfg80211.ko") < wifi.index("/qca_cld3_qca6750.ko")
assert "on property:post.decrypt.modules=true\n    start aera-wlan-ready" in wifi
assert "/vendor/firmware_mnt/image" in wifi
qcom = (root / "init.recovery.qcom.rc").read_text()
assert "modem${ro.boot.slot_suffix}" in qcom
assert "mount none /firmware /vendor/firmware_mnt bind" in qcom
assert not re.search(r"^\s*mount ", wifi, re.M), "Do not stack firmware/persist mounts"
assert {"msm_kgsl.ko", "machine_dlkm.ko"} <= set(early)
assert {"pinctrl_lpi_dlkm.ko", "wcd9378_slave_dlkm.ko", "stub_dlkm.ko", "btfm_slim_codec.ko", "hdmi_dlkm.ko", "audio_pkt_dlkm.ko", "frpc-adsprpc.ko",
        "lpass_cdc_va_macro_dlkm.ko", "lpass_cdc_tx_macro_dlkm.ko",
        "lpass_cdc_wsa_macro_dlkm.ko"} <= set(early), \
    "The machine audio card needs the stub codec, external-display codec, DSP IPC, WCN6750 endpoint and enabled LPASS macros"
for name in ("stub_dlkm.ko", "btfm_slim_codec.ko", "hdmi_dlkm.ko", "audio_pkt_dlkm.ko", "frpc-adsprpc.ko"):
    assert canonical(name) in installed, f"Required audio provider missing from ROM: {name}"
    assert early.index(name) < early.index("machine_dlkm.ko")
assert "btfm_slim_codec.ko" in deferred
assert "bt_fm_swr.ko" not in early + deferred
assert "lpass_bt_swr_dlkm.ko" not in early
assert "wifi.driver.ready true" in wifi and "timeout_period 60" in wifi
assert "-O/tmp/recovery/sockets" in wifi and " -dd " not in wifi
assert wifi.count("mkdir /tmp/recovery 0770 root wifi") == 2
assert wifi.count("mkdir /tmp/recovery/sockets 0770 wifi wifi") == 2
assert (root / "vendor/etc/wifi/qca6750/WCNSS_qcom_cfg.ini").read_bytes() == \
       (dump / "vendor/etc/wifi/qca6750/WCNSS_qcom_cfg.ini").read_bytes()
for name in ("rmnet_wlan.ko", "wlan_firmware_service.ko"):
    assert not (root / "lib/modules" / name).exists(), f"Stale bundled WLAN module: {name}"
    assert canonical(name) not in (root / "system/bin/runatboot.sh").read_text().split('DRIVERS="')[1].split('"')[0].split()

for path in tree.glob("*.mk"):
    assert not re.search(r"^\s*(TW_|TWRP_|OF_|FOX_)\w+\s*[:?+]?=", path.read_text(), re.M), \
        f"Legacy recovery flag remains in {path.name}"
print(f"PASS: {len(deferred)} installed-ROM modules, dependency order, ICNSS startup, stock config and AERA flags")
