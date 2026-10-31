# Run from the device-tree root:
# make -f tests/aera_flags.mk AERA_SOURCE=/path/to/aera
ifndef AERA_SOURCE
$(error Set AERA_SOURCE to the Android source root)
endif

include aera.mk
include aera_config.mk
include $(AERA_SOURCE)/bootable/recovery/aera_config.mk

ifneq ($(AERA_BUILD_TYPE),Beta)
$(error FroggerPro test builds must not default to Stable)
endif
ifneq ($(OF_ADVANCED_SECURITY),0)
$(error Init-managed debug ADB must not be stopped by advanced security)
endif
ifneq ($(OF_ENABLE_WLAN),1)
$(error AERA_ENABLE_WLAN did not enable the Wi-Fi backend)
endif
ifneq ($(TW_POST_DECRYPT_MODULES),$(AERA_POST_DECRYPT_MODULES))
$(error Deferred WLAN modules were not passed to the module loader)
endif
ifneq ($(TW_LOAD_VENDOR_MODULES),$(AERA_LOAD_VENDOR_MODULES))
$(error Early module configuration was not translated)
endif
ifneq ($(TW_INCLUDE_CRYPTO_FBE),true)
$(error FBE support was lost during flag conversion)
endif
ifneq ($(TW_SUPPORT_INPUT_AIDL_HAPTICS),true)
$(error AIDL haptics support was lost during flag conversion)
endif
ifneq ($(TW_SUPPORT_INPUT_AIDL_HAPTICS_FQNAME),"IVibrator/default")
$(error AIDL vibrator instance changed)
endif
ifneq ($(TW_EXCLUDE_DEFAULT_USB_INIT),true)
$(error Device USB init configuration was lost)
endif
ifneq ($(AERA_UI_ADAPTIVE_RESOLUTION),true)
$(error Adaptive UI resolution is not enabled)
endif
ifneq ($(AERA_SCREEN_H),2400)
$(error 1260x2800 panel must use 2400 reference height)
endif
ifneq ($(AERA_DEFAULT_LANGUAGE),en)
$(error Default UI language is not English)
endif

.PHONY: check
check:
	@printf '%s\n' 'AERA Wi-Fi, module staging, crypto, haptics, USB and adaptive UI flags passed'
