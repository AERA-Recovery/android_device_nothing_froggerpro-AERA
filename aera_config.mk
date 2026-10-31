# ------------------
# AERA recovery configuration
# ------------------

# Display
TARGET_SCREEN_DENSITY := 440
TARGET_SCREEN_HEIGHT := 2800
TARGET_SCREEN_WIDTH := 1260
AERA_CUSTOM_CLOCK_POS := "590"

# Recovery UI
AERA_THEME := portrait_hdpi
AERA_SCREEN_BLANK_ON_BOOT := true
AERA_INPUT_BLACKLIST := "null"

AERA_MAX_BRIGHTNESS := 5000

AERA_DEFAULT_LANGUAGE      := en
AERA_USE_TOOLBOX           := true
AERA_INCLUDE_NTFS_3G       := true
AERA_INCLUDE_FUSE_EXFAT    := true
AERA_INTERNAL_STORAGE_PATH := "/data/media/0"
AERA_INCLUDE_FUSE_NTFS     := true
AERA_INCLUDE_REPACKTOOLS   := true
AERA_INCLUDE_LIBRESETPROP  := true
AERA_INCLUDE_RESETPROP     := true
AERA_EXTRA_LANGUAGES       := true
AERA_EXCLUDE_APEX          := true
AERA_INCLUDE_FASTBOOTD     := true

# The card also requires the stub codec and the WCN6750 Slimbus endpoint;
# these ASoC components are not all hard dependencies of machine_dlkm.
# Stock also enables the external-display audio link. Load the ROM's copies.
AERA_LOAD_VENDOR_MODULES := "socinfo.ko qcom_iommu_util.ko pinctrl-msm.ko msm_kgsl.ko adsp_loader_dlkm.ko rproc_qcom_common.ko q6_dlkm.ko qcom_q6v5.ko qcom_q6v5_pas.ko qcom_sysmon.ko smem.ko btpower.ko btfmcodec.ko btfm_slim_codec.ko pinctrl_lpi_dlkm.ko wcd9378_slave_dlkm.ko lpass_cdc_va_macro_dlkm.ko lpass_cdc_tx_macro_dlkm.ko lpass_cdc_wsa_macro_dlkm.ko stub_dlkm.ko hdmi_dlkm.ko audio_pkt_dlkm.ko frpc-adsprpc.ko machine_dlkm.ko aw882xx_dlkm.ko tfa98xx_dlkm.ko"
AERA_LOAD_VENDOR_MODULES_EXCLUDE_GKI := true

# The init WLAN action consumes these staged modules before the decrypt prompt.
# Retain the deferred list for an idempotent retry after decryption.
# Installed-ROM modules, staged by AERA before vendor/system_dlkm unmount.
# The stock modem image contains qca6750/wpss.mdt and qca6750 BDFs: this is
# the integrated ICNSS/WPSS path, not Lighthouse's external CNSS/Peach path.
AERA_POST_DECRYPT_MODULES := "qcom_ramdump.ko qmi_helpers.ko pdr_interface.ko qcom_va_minidump.ko smem-mailbox.ko cnss_prealloc.ko cnss_utils.ko cnss_nl.ko wlan_firmware_service.ko rfkill.ko btpower.ko btfmcodec.ko btfm_slim_codec.ko cfg80211.ko icnss2.ko qca_cld3_qca6750.ko"

# Haptics
AERA_SUPPORT_INPUT_AIDL_HAPTICS := true
AERA_SUPPORT_INPUT_AIDL_HAPTICS_FQNAME := "IVibrator/default"
AERA_SUPPORT_INPUT_AIDL_HAPTICS_FIX_OFF := false

# CPU Temperature
AERA_CUSTOM_CPU_TEMP_PATH := /sys/class/thermal/thermal_zone17/temp

# USB
AERA_EXCLUDE_DEFAULT_USB_INIT := true
AERA_USE_SERIALNO_PROPERTY_FOR_DEVICE_ID := true

# Little hack (some reason libhardware.so isn't ending up compiled)
TARGET_RECOVERY_DEVICE_MODULES += \
    android.hidl.allocator@1.0 \
    android.hidl.memory@1.0 \
    android.hidl.memory.token@1.0 \
    libdmabufheap \
    libhidlmemory \
    libhardware \
    libion \
    libnetutils \
    libnativewindow \
    libui \
    libgralloctypes \
    android.hardware.graphics.common-V6-ndk \
    vendor.display.config@1.0 \
    vendor.display.config@2.0 \
    libdebuggerd_client

AERA_OVERRIDE_SYSTEM_PROPS := \
    "ro.build.product;ro.build.fingerprint=ro.vendor.build.fingerprint;ro.build.version.incremental"
AERA_OVERRIDE_PROPS_ADDITIONAL_PARTITIONS := vendor
RECOVERY_LIBRARY_SOURCE_FILES += \
    $(TARGET_OUT_SHARED_LIBRARIES)/android.hidl.allocator@1.0.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/android.hidl.memory@1.0.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/android.hidl.memory.token@1.0.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libdmabufheap.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libhidlmemory.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libion.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libnetutils.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libnativewindow.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libui.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libgralloctypes.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/android.hardware.graphics.common-V6-ndk.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libdebuggerd_client.so \
    $(TARGET_OUT_SYSTEM_EXT_SHARED_LIBRARIES)/vendor.display.config@1.0.so \
    $(TARGET_OUT_SYSTEM_EXT_SHARED_LIBRARIES)/vendor.display.config@2.0.so
AERA_FRAMERATE := 144
AERA_HAS_EDL_MODE := true

# Encryption
AERA_INCLUDE_CRYPTO := true
AERA_INCLUDE_CRYPTO_FBE := true
AERA_INCLUDE_FBE_METADATA_DECRYPT := true
# Stock advertises SIM1/SIM2, not the embedded eSE1 required by se_omapi.
# FBE uses the existing QTI KeyMint/Gatekeeper stack, not a borrowed eSE HAL.
AERA_INCLUDE_OMAPI := false

# Debug
TARGET_USES_LOGD := true
AERA_INCLUDE_LOGCAT := true
TARGET_RECOVERY_DEVICE_MODULES += debuggerd
RECOVERY_BINARY_SOURCE_FILES += $(TARGET_OUT_EXECUTABLES)/debuggerd
TARGET_RECOVERY_DEVICE_MODULES += strace
RECOVERY_BINARY_SOURCE_FILES += $(TARGET_OUT_EXECUTABLES)/strace
