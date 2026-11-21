#!/usr/bin/env bash
# Chuyen doi A<->B N lan: restore -> launch -> doi -> doc danh tinh -> chup man hinh
export MSYS_NO_PATHCONV=1; ADB=/d/LDPlayer/LDPlayer9/adb.exe; S=emulator-5568; P=com.ageofwarpath.globalwarzone.vn
N=${1:-3}
for i in $(seq 1 $N); do for slot in guestA guestB; do
  t0=$(date +%s%3N)
  bash slot.sh restore $slot 2>&1 | grep -E 'restore|ERROR|FAIL'
  t1=$(date +%s%3N)
  $ADB -s $S shell input keyevent KEYCODE_WAKEUP
  $ADB -s $S shell "am start -W -n $P/com.revengeofempire.plugins.MainActivity" | grep -oE 'TotalTime: [0-9]+'
  sleep 45
  pid=$($ADB -s $S shell pidof $P | tr -d '\r')
  id=$(bash ident.sh | awk '/JOY_ACCOUNT_ID|account_uuid/{printf "%s=%s ",$1,$2}')
  case $slot in guestA) exp=c17651d4d1;; guestB) exp=b788ba2ef8;; esac; ok=FAIL; [ -n "$pid" ] && echo "$id" | grep -q "JOY_ACCOUNT_ID=$exp" && ok=PASS
  echo "$ok round=$i slot=$slot restore_ms=$((t1-t0)) pid=${pid:-DEAD} $id"
  $ADB -s $S exec-out screencap -p > "logs/sw_${i}_${slot}.png" 2>/dev/null
done; done
