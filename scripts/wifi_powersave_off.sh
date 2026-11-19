#!/usr/bin/env bash
# Persistently disable Wi-Fi power save (needs sudo). Do not restart NetworkManager.
set -euo pipefail
if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo -n "$0" "$@" 2>/dev/null || exec sudo "$0" "$@"
fi

CONF=/etc/NetworkManager/conf.d/default-wifi-powersave-on.conf
if [[ -f "$CONF" ]]; then
  sed -i 's/^wifi.powersave *=.*/wifi.powersave = 2/' "$CONF"
else
  printf '[connection]\nwifi.powersave = 2\n' >"$CONF"
fi

if command -v nmcli >/dev/null; then
  while IFS=: read -r name uuid _type _dev; do
    [[ -z "$name" ]] && continue
    nmcli connection modify "$uuid" 802-11-wireless.powersave 2 2>/dev/null || true
  done < <(nmcli -t -f NAME,UUID,TYPE,DEVICE connection show | awk -F: '$3=="802-11-wireless"{print}')
fi

if command -v iwconfig >/dev/null; then
  iwconfig wlan0 power off 2>/dev/null || true
fi
echo "wifi.powersave=2 written. current:"
grep -H . "$CONF" || true
iwconfig wlan0 2>/dev/null | grep -E 'ESSID|Power Management' || true
