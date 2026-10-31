#!/system/bin/sh

# Load touch drivers if they didn't load
# Adapted from chickendrop89

DRIVERS="panel_event_notifier qts goodix_ts st_fts touchpanel_event_notify ft3683g atmel_mxt_ts gpu_dump_skip_cdev"
MODULES_DIR="/lib/modules"

# Some ROM kernels supply focaltech_fts instead of the stock ft3683g driver.
# Never insert a second touchscreen stack over an already bound ROM driver.
TOUCH_READY=0
for d in focaltech_fts ft3683g goodix_ts st_fts atmel_mxt_ts; do
  if [ -d "/sys/module/$d" ]; then
    TOUCH_READY=1
    break
  fi
done

for d in $DRIVERS; do
  if [ "$TOUCH_READY" = 1 ] && [ "$d" != gpu_dump_skip_cdev ]; then
    continue
  fi
  lsmod | grep -q "^$d" && continue
  path=$(find "$MODULES_DIR" -name "$d.ko" | head -n 1)
  if [ -f "$path" ]; then
    if insmod "$path"; then
      echo "Force inserted module: $d" >>/tmp/modules.log
    else
      echo "Failed to insert fallback module: $d" >>/tmp/modules.log
    fi
  fi
done

