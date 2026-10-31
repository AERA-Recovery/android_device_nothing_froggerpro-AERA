#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Select the device before sourcing envsetup, as in the README build command.
# Do not enable packaging options when another device is selected.
case "${AERA_BUILD_DEVICE:-${TARGET_PRODUCT:-${1:-}}}" in
    froggerpro|twrp_froggerpro|twrp_froggerpro-*)
        # Plugin Manager uses this static binary's wget HTTPS downloader.
        export AERA_USE_BUSYBOX_BINARY=1
        ;;
esac
