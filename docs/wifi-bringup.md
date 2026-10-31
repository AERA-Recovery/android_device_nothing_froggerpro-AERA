# FroggerPro Wi-Fi bring-up

This is a device-tree-only correction of the initial Wi-Fi setup. No common
AERA source changes or replacement firmware/kernel modules are required.

## Stock evidence

- Stock `vendor/etc/init/init.vendor.wlan.rc` starts integrated WPSS with
  `/sys/kernel/icnss/wlan_en_delay` and `/sys/kernel/icnss/wpss_boot`.
- The Kera base DTB requests `qca6750/wpss.mdt`. The dumped active firmware
  package (`modem.img`) contains that image and QCA6750 BDF/regulatory files.
- Stock `qca_cld3_qca6750.ko` depends on `icnss2`, `cfg80211`,
  `cnss_prealloc`, `cnss_utils`, `cnss_nl` and `qcom_va_minidump`.
- The copied QCA6750 INI matches the dump byte-for-byte and is retained.
  Its firmware aliases and per-device MAC path under persist are also retained.

The old recovery configuration had an unimported Wi-Fi RC, no deferred WLAN
host-driver list, and a Lighthouse-style CNSS/Peach `fs_ready` path. Loading
only `wlan_firmware_service` and `rmnet_wlan` cannot create `wlan0`.

## Changes

- Import Wi-Fi init, stage the ordered WLAN dependency list from the installed
  ROM, and start WPSS after the post-decryption module stage.
- Include `socinfo`, `qcom_iommu_util` and `pinctrl-msm` in the early module
  request list; ICNSS needs these vendor-boot prerequisites before its deferred
  module can bind. Their dependencies are resolved by the early module loader.
- Mount active-slot modem firmware and original persist data read-only in fs.
  Bind the single firmware mount at `/vendor/firmware_mnt`, shared by ADSP and
  WLAN; do not stack new mounts after decryption.
- Wait for a real `wlan0` before declaring driver readiness; bound the waiter
  to 60 seconds and keep the normal AERA supplicant service/control socket.
- Remove the two stale bundled Wi-Fi-related modules from the ramdisk and
  their unconditional boot-script insertion. Existing haptic/touch modules
  are not changed by this Wi-Fi correction.
- Keep all recovery settings in BoardConfig-included `aera.mk` and
  `aera_config.mk`, convert supported legacy flags to AERA names, enable
  adaptive UI sizing, and retain the existing English/crypto/haptics settings.
- `AERA_ENABLE_WLAN := 1` was already present. It is retained and tested;
  it was not the missing driver/init wiring.

## Offline checks

From this tree's root:

```
make -f tests/aera_flags.mk AERA_SOURCE=/path/to/AERA_16.0
python3 tests/check_wifi.py /path/to/extracted/FroggerPro
/path/to/AERA_16.0/out/host/linux-x86/bin/host_init_verifier recovery/root/init.recovery.wifi.rc
```

These checks do **not** prove a successful boot or Wi-Fi connection. The
multi-device stock DTBO contains other WLAN variants; a recovery kernel log
must confirm the running FroggerPro board binds to the QCA6750/ICNSS path.
Do not enable every QCA host-driver variant at once to hide a mismatch.

## Runtime corrections from the first AERA log

- Set the adaptive reference height to 2400 for the 1260x2800 display, yielding
  a 1440x3200 logical canvas rather than 1440x3733.
- Include stock `libadreno_utils` and `libgsl`, plus source-built
  `libnativewindow`, and audit the packaged GPU dependency closure.
- Keep the shared `prepdecrypt.sh`, but declare its service locally and remove
  the legacy HIDL crypto init templates. Preserve the existing vendor
  KeyMint/Gatekeeper stack and preparation trigger.
- Start qseecomd after filesystem setup. Remove the mismatched Thales/eSE1
  service and OMAPI client: stock exposes SIM1/SIM2, not eSE1. Preserve
  KeyMint/Gatekeeper and retain one boot-control service declaration.
- Skip fallback touchscreen insertion when a ROM touchscreen module is already
  loaded (the tester kernel provides `focaltech_fts`). Preserve the stock
  fallback for kernels without a loaded touchscreen driver.

After building, run `python3 tests/check_runtime.py /path/to/recovery/root`.
Passing this ELF/file audit does not prove hardware GPU initialization or
successful decryption; those still need the next device log.

## USB/ADB corrections

The recovery log showed common init binding `g1` successfully, followed by a
second device action changing IDs and failing another bind with `EBUSY`.
The old device RC also mounted ADB/fastboot FunctionFS a second time, created
children of a nonexistent `g2`, and bound the gadget unconditionally at boot.

The device RC now selects configfs in early-init and resolves the boot-supplied
controller before common init's fs actions. The known fallback `a600000.dwc3`
is confirmed by the recovery log and the stock `a600000.ssusb` controller path.
Stock USB setup was used as a controller/function reference, not copied as a
second Android USB HAL alongside recovery's own gadget management.

Common init remains the sole owner of ADB/sideload/fastboot bindings and their
FunctionFS mounts. The device RC adds only MTP, requires both descriptor-ready
signals for MTP+ADB, and uses one vendor ID with mode-specific product IDs from
`system.prop`. The existing peripheral-role initialization is retained but
moved before binding, with a bounded wait for UDC registration. It no longer
forces ADB again at boot (which could overwrite another requested mode).

Run `python3 tests/check_usb.py /path/to/AERA_16.0`, and repeat with
`--ramdisk /path/to/recovery/root` after building. This is an action/packaging
audit, not an on-device USB enumeration test.

## Development build policy

FroggerPro bring-up images explicitly use `AERA_BUILD_TYPE := Beta` and
`AERA_ADVANCED_SECURITY := 0`. A Stable build implicitly enables legacy
advanced security, whose recovery startup code stops an otherwise working
init-managed ADB daemon before the decrypt page and disables automatic MTP.
The tester log confirmed this exact `ctl.stop` from recovery after USB was
already configured successfully. This is separate from USB gadget setup.

Beta intentionally leaves debug/root ADB available before decryption. Do not
launch an unmanaged `adbd` from `runatboot.sh`; init must provide its sockets
and own its lifecycle. Revisit the security policy before a stable release.
Export `AERA_BUILD_TYPE=Beta` in the build shell too, so packaging scripts
using the environment label the artifacts consistently with compiled recovery.

## GPU and audio follow-up

- Request the installed ROM's `msm_kgsl` and machine audio modules early; the
  early loader resolves their dependency closure. Do not ship dump modules.
- Start stock PD mapper, DSP service and audio FastRPC transport in post-fs,
  before the SPF deferred-probe window. Do not reboot an already running ADSP.
- Mount the active physical DSP partition read-only. Ship the matched AGM/PAL
  userspace dependency closure and Kera speaker/ACDB configuration in the
  ramdisk, isolated from the GPU/crypto library search path. No persistent
  logical system/vendor/odm mounts are needed by audio.
- Build a protected PCM bridge for browser/media. Its bounded bootstrap only
  succeeds after both AGM and PAL Binder services register.
- Fix malformed ueventd sysfs rules and the duplicate dma_heap subsystem.
- Use FroggerPro's RichTap configuration, give the vibrator service an explicit
  recovery domain and grant its ICS device-node access. Do not overwrite
  persist calibration or manufacture missing SFDC calibration values.

`tests/stage_audio_runtime.py /path/to/FroggerPro` reproduces unmodified stock
audio assets. After building, run `tests/check_audio.py` against the packaged
root as well as the USB/GPU audits. Offline checks do not prove hardware
initialization, speaker output, or Bluetooth/headset support.

## Device validation

Test a clean boot, complete decryption (or boot without a screen lock), then
turn Wi-Fi on, scan, connect to WPA2 and WPA3 networks, obtain DHCP/DNS, and
turn Wi-Fi off/on. Also check the recovery/fastbootd round trip.

Capture these after a failed attempt:

```
adb shell getprop post.decrypt.modules
adb shell getprop wifi.driver.ready
adb shell getprop init.svc.wpa_supplicant
adb shell uname -r
adb shell cat /proc/modules
adb shell ls -l /sys/kernel/icnss /sys/class/net
adb shell cat /proc/mounts
adb shell dmesg > froggerpro-wifi-dmesg.txt
adb logcat -b all -d > froggerpro-wifi-logcat.txt
adb pull /tmp/recovery.log froggerpro-recovery.log
```

The log should show staged/loaded ICNSS and QCA6750 modules, WPSS firmware
startup, `wlan0`, supplicant control readiness and DHCP. Missing symbols,
kernel-version mismatches or different hardware binding need a tester log,
not another device's prebuilt modules.

## Follow-up from the October 30 log

The log shows init-managed ADB and haptic playback, but EGL initialization
fails, ADSP automatic firmware loading fails before the firmware mount exists,
and the health HAL never sees a battery. No WLAN bring-up follows the decrypt
screen. These corrections remain confined to this device tree:

- Start a bounded ADSP readiness service after firmware is mounted, selecting
  the processor by name and starting it only if it is not already running.
  This also brings up the ADSP-hosted charger protection domain. Do not wait
  synchronously in init for a battery device which depends on that startup.
- Load the staged installed-ROM WLAN modules in the `twrp.modules.loaded`
  action, including the versioned system_dlkm rfkill dependency, so choosing
  Skip on the decrypt page does not prevent WLAN initialization. Preserve the
  normal post-decryption retry and avoid restarting WPSS at that point.
- Include the installed Bluetooth SoundWire endpoint and its dependencies;
  the machine audio driver may depend on those DAIs even for speaker playback.
- Replace the mixed GPU userspace with dump-matched EGL subdrivers and vendor
  dependencies. Include gralloc.default and dynamically loaded Adreno profile
  and format helpers; audit the subdriver ELF dependencies as well as the
  primary EGL/GLES libraries. `tests/stage_gpu_runtime.py` reproduces these
  stock vendor assets without replacing shared platform/crypto libraries.
- Keep PAL loaded for the disposable playback worker lifetime, including a
  failed initialization, to avoid unloading code below vendor worker threads.

A successful image build and offline audits do not prove on-device Wi-Fi,
speaker output, battery reporting, GPU initialization or fastbootd transition.
The GPIO-reference warnings also require comparison with the tester's running
kernel/device tree; this recovery-only build does not replace their boot,
vendor_boot or DTBO partitions.

## Follow-up from logcat (5) and recovery (3)

The October 30 build gets past the previous EGL initialization failure, but
recovery aborts in GraphicBufferMapper: the native `mapper.qti.so` runtime
and the allocator HAL were missing. The recovery log repeats startup because
of this abort; no interactive audio or network connection test completes.
The health HAL does report a real 95–96% capacity, and WLAN creates wlan0.

- Ship stock native Mapper5, its HAL/general-search aliases, the stock AIDL
  allocator binary, SnapAlloc runtime, and their dependency closure. Copy the
  stock native-mapper and allocator VINTF fragments and start the allocator
  from post-fs before recovery's UI starts. Do not inherit SurfaceFlinger
  restarts from Android's allocator init file.
- Give `/tmp/recovery` group traversal to wifi and make the control directory
  owned by wifi. Android supplicant's `os_program_init()` switches to AID_WIFI
  even when init starts it as root; the previous root:root 0770 directories
  therefore caused a real Unix permission error, independent of permissive
  SELinux.
- Extend the packaging audit with the dlopen-only mapper/allocator files,
  VINTF entries, startup wiring and Wi-Fi directory ownership so these omissions
  are caught before the next hardware test.

These are incremental changes for the same device; no clean/clobber or common
recovery source edits are needed.

## Follow-up from logcat (6)

The corrected mapper stops the recovery crash loop. WPA key negotiation,
association, DHCP ACK and interface configuration succeed, and the native UI
reports real battery charge/capacity. Decryption completion also reaches the
all-users-decrypted init action.

GPU fallback now has a narrower cause: SnapAlloc logs missing configuration
files and rejects RGBA_8888 (format 1), so native scanout allocation fails even
though EGL, mapper and allocator initialization succeed. Ship the eight stock
format/alignment JSON files in the ramdisk before the allocator caches those
tables at startup. Check JSON parsing and the RGBA_8888 format explicitly.

The sound card remains deferred because RX waits for the unregistered VA
macro. Request the enabled VA, TX and WSA macro modules from the installed ROM
in addition to the RX dependency pulled in by machine_dlkm. Do not ship .ko
files or alter the flashed DTBO to work around a missing module request.
Speaker playback and hardware scanout still need the next on-device test.

## Follow-up from logcat (7)

The UI now confirms `zero-copy native-buffer GPU ready`, Adreno 722 and
zero-copy Adreno/LVGL rendering. Startup animation submissions reach roughly
100–120 fps. There are no fatal signals; WPA association/DHCP and battery
reporting continue to work. Some later isolated LVGL drawing errors remain;
the log does not show a context loss or recovery restart from them.

Audio still fails because the VA macro cannot obtain its SoundWire pin state.
All four codec pinctrl devices remain deferred, and no LPI pin-controller
module is loaded. The installed `pinctrl_lpi_dlkm.ko` advertises the exact
`qcom,lpi-pinctrl` compatible used by this board, so request that module with
the other early audio modules, using the ROM's copy and dependency resolver.

The allocator also logs EACCES opening `/dev/qti-smmu-proxy`, which stock
ueventd owns as system:system 0660. Give only the allocator service the system
supplementary group; retain the stock device-node permissions.

## Follow-up from logcat (8)

The LPI pin-controller request works: VA, RX and TX macros now register and
only the machine sound card remains deferred. The installed machine module
includes WCD9378 links, and the log shows the WCD9378 parent probe but no
WCD9378 SoundWire slave driver. Its component-master bind waits for both slave
components. Explicitly request the matching installed `wcd9378_slave_dlkm.ko`;
the WCD939x slave pulled in by the module dependency table is not its provider.

Also include `libsndcardparser` and the stock AGM PCM/mixer/compress plugins.
TinyALSA/AGM resolve those dynamically, so a DT_NEEDED-only dependency walk
missed them. They remain inside the isolated stock audio library directory.

On a remaining card-registration timeout, save ALSA cards, ASoC components,
DAIs, deferred devices, codec names, SoundWire bindings and loaded modules to
`/tmp/aera-audio-state.txt` once. Copy a bounded version to the kernel log.
If debugfs is not already available, use a temporary read-only debugfs view
under tmpfs and unmount it after the capture. This does not mount or modify
any persistent partition.

## Follow-up from logcat (9)

Both WCD9378 SoundWire slaves now bind, and `wcd9378-codec` plus its DAI
appear in the diagnostic capture. The sound card still defers: its actual
`asoc-codec-names` includes `msm-stub-codec.1`, but no stub component or
`msm-stub-rx`/`msm-stub-tx` DAIs have registered. Request the installed
`stub_dlkm.ko` before the machine driver. The machine driver's hard module
dependencies do not express this ASoC component dependency.

The BT transport driver is loaded but its hardware endpoint and ASoC DAIs
are absent. The stock device tree has an LPASS BT SoundWire controller,
and stock modules.load explicitly loads `lpass_bt_swr_dlkm.ko`. Request
that installed module as well: it creates the controller on which the BT
SoundWire slave binds and registers its codec endpoint. Do not substitute
the unrelated Slimbus transport or ship kernel modules in the ramdisk.

Hardware Adreno rendering remains confirmed in this log. Speaker output
still needs the next build tested; this log never gets as far as PAL setup.

## Follow-up from logcat (10)

The stub component and both stub DAIs now register. The BT SoundWire master
also appears as swr4, but has no slave or codec endpoint. Loading the generic
BT SoundWire controller was insufficient and was the wrong transport for this
board's WCN6750 endpoint: the stock overlay describes `btfmslim-driver` under
the enabled Slimbus NGD node, compatible `slim217,221`, with RX channels
157/158 and TX channels 159/160. The log confirms the Slimbus controller is
already present, but `btfm_slim_codec` has never been loaded.

Replace the SoundWire BT request with the installed `btfm_slim_codec.ko` in
both the early module list and the staged pre-decrypt init action. Remove
the added BT SoundWire master request; keep the codec's RX/VA SoundWire
drivers. The matched Slimbus driver registers the missing btfmcodec audio
endpoint through its hardware-endpoint interface. No Bluetooth power-up or
firmware replacement is added. Extend timeout diagnostics with Slimbus
devices, drivers and compatibles so the next log can confirm binding.

The machine card still has no ALSA control node in this log; audio remains
unverified until the next on-device test.

## Follow-up from logcat (11)

The correct Slimbus driver now binds to `217:221:1:0` and registers
`btfmcodec_dev`, `btaudio_rx` and `btaudio_tx`. The stub, WCD9378, LPASS RX/TX/VA
and both Awinic speaker codecs are registered, but the machine card still
defers before PAL can start.

Inspecting the stock QRD/Awinic overlay (DTBO entry 43, also present in the
related 46/49 variants) reveals `qcom,ext-disp-audio-rx = <1>`. The generic
MTP overlay examined earlier had this disabled and did not match the live
codec-name list. The QRD overlay exactly matches the logged WCD9378 codec
names and the two Awinic speakers. The machine driver therefore adds the
external-display link, whose `msm_dp_audio_codec_rx_dai` provider is absent
from the captured ASoC DAIs.

Request the ROM's `hdmi_dlkm.ko` before `machine_dlkm.ko`, resolving its
`msm_ext_display` dependency normally. The first-stage generic
`snd-soc-hdmi-codec` does not supply this Qualcomm-specific codec. Keep the
flashed device tree unchanged. Extend timeout capture with the live sound
card link settings to distinguish enabled optional backends in future logs.

## Follow-up from logcat (12)

The kernel now registers `kera-qrd-snd-card` successfully, including the
external-display codec. AGM enumerates its backend PCM devices and loads
the Kera QRD calibration. It fails next in GSL's SPF readiness check because
the GPR wrapper finds no `/dev/aud_pasthru_adsp` and therefore has no send
function. This is no longer an ALSA registration failure.

Request the installed `audio_pkt_dlkm.ko`, including its dependency closure
(`audpkt_ion_dlkm`, GPR, SPF and IPC logging). Its `qcom,audio-pkt` and
`qcom,audio-pkt-core-platform` compatibles match the stock device tree, and
it creates the ADSP packet transport. The stock ueventd ownership rule is
already present and the isolated AGM service already has the audio group.
Do not create a fake node, substitute `/dev/gpr_channel`, or change the
calibration files to mask the absent transport.

Wait for the actual character device before starting AGM. If it does not
appear, fail with the specific transport error and capture diagnostics
instead of repeatedly initializing AGM with an empty IPC table. The
temporary diagnostic report also includes the transport-node state.

## Follow-up from logcat (13)

The ADSP packet node is present, shared-memory initialization opens
`/dev/msm_audio_ion`, and GPR now communicates with the running audio PD.
AGM progresses to dynamic module loading, but audioadsprpcd repeatedly times
out in `fastrpc_wait_for_secure_device`, explicitly reporting that the FastRPC
driver is disabled. No `frpc-adsprpc` module has been requested.

Load the installed `frpc-adsprpc.ko` and its dependency closure. Its
`qcom,fastrpc` compatible matches the stock GLINK device tree. Preserve the
stock normal/secure device-node permissions already in ueventd.

Also ship the stock root-PD `adsprpcd` executable beside audioadsprpcd, in
the same isolated library environment. Start both listeners after early
module loading, matching stock's rootpd/adsp and audiopd/adsp roles, before
a user requests playback. Before starting AGM, verify the actual normal and
secure ADSP FastRPC character devices as well as the packet device. Keep
DSP files on the mounted active-slot DSP partition and do not alter the
stock calibration to suppress the dynamic-module error. Whether module
loading and speaker playback succeed still requires the next hardware log.

This log also contains a SIGSEGV in an AGM Binder thread immediately after
registration fails. The local host had dlclosed the vendor service library
while its Binder/GPR workers could still be running. Keep vendor libraries
mapped for the host process lifetime and use `_exit(70)` on post-load fatal
errors, so the kernel reclaims code and threads together. This change is
confined to the device-local AGM host and does not change common recovery.

## Follow-up from logcat (14)

FastRPC now probes successfully, opens its ADSP RPMsg channel, registers
audio-PD service lookup, and creates `/dev/fastrpc-adsp-secure`. The added
readiness guard was too strict: this is a secure ADSP domain and does not
need to expose `/dev/fastrpc-adsp`. Only NSP domains additionally register
the non-secure legacy node in the matched driver design. Remove that
requirement; do not fabricate an alias or change node permissions.

Both listener starts from `twrp.modules.loaded` fail with ENOENT while the
ROM vendor mount covers the ramdisk executables. Remove those early starts
and retain ordered startup in the playback bootstrap, after its packet and
secure FastRPC checks. Explicitly wait for the ramdisk listener executables
and isolated `libadsprpc.so` to be visible before asking init to start them.
This also avoids starting a process against temporarily hidden dependencies.

The current log confirms the ALSA card and both DSP transport drivers; it
does not reach AGM because the incorrect non-secure-node guard stopped it.

## Hardware confirmation from logcat (15)

The tester confirms audible sound. The log now shows successful AGM and PAL
Binder registration, both Awinic speaker amplifiers reporting `start success`,
and `pal_stream_start` completing with status 0 on repeated playback. The
previous missing-node and dynamic-module startup failures are resolved in
this tested configuration. Hardware Adreno rendering remains confirmed, and this capture contains
no fatal signals.

The log is not completely clean: ATS retries because Diag is unavailable,
PAL reports missing optional VoiceUI/statistics/performance clients, and the
speaker-feedback/custom-event path reports unsupported event registration
(-95) and missing calibration entries. These do not prevent the observed
speaker playback, but the feedback/calibration warnings remain open for
separate investigation. This test does not establish fastbootd transitions,
headset routing, or every media format.

Keep the working runtime and installed-ROM module requests unchanged while
recording this baseline. The tested log-14 build's image SHA-256 is
`3639637f4715d15c44159ff29c6d7e1bf08b0ab69dc05147f4accaecf4778f13`.

## Catalog downloader and haptics packaging

The diagnostic reports successful WPA2 association and DHCP, but the tested
image contains no BusyBox. Plugin Manager invokes `busybox wget` directly.
Enable `AERA_USE_BUSYBOX_BINARY=1` in a device-guarded vendorsetup hook, as
in the other AERA device trees. Recovery startup already restores `/sbin/*`
executable permissions; no extra product copy or init chmod is needed.

The stock RichTap node `/dev/aw86927_haptic` is correct for this RT6010
driver. The original vibrator HAL cannot start while its `/vendor` path
is covered by the mounted ROM. Package the matching executable, its two
private libraries and configuration under ramdisk `/system` paths and point
the existing vibrator service at them. Keep the original kernel-module
trigger, haptic permissions and direct HAL startup unchanged; no new
bootstrap service or delay is necessary. No global library is replaced.

The following failed-UI log confirms AAC initialization and registration of
`android.hardware.vibrator.IVibrator/default`. It also records an earlier
first-stage display failure: SDE CESTA cannot acquire its interconnect path
(-517), DRM never registers, and recovery later crashes without a display.
The known-working and failed images contain identical recovery and graphics
binaries. Keep this display failure separate from claims of confirmed haptic
output; the new minimal packaging still requires testing on the device.
