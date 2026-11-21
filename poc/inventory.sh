#!/usr/bin/env bash
# Kiem ke tai khoan tren tung instance (CHI DOC du lieu game; khong mo game).
# Moi instance: backup .ldbk -> bat root -> boot -> doc danh tinh (hash) -> tat -> tra root ve nhu cu.
# Dung: inventory.sh 0 1 2 ...
set -uo pipefail
export MSYS_NO_PATHCONV=1
LD=/d/LDPlayer/LDPlayer9/ldconsole.exe; ADB=/d/LDPlayer/LDPlayer9/adb.exe
P=${P:-com.ageofwarpath.globalwarzone.vn}
ROOT=$(cd "$(dirname "$0")" && pwd); OUT=${OUT:-$ROOT/logs/inventory.csv}; BK=/e/AOW-BOT/backups
[ -f "$OUT" ] || echo "idx,name,root_before,backup_gb,backup_s,installed,version,joy_id,account_uuid,game_uid,device_uid,android_id,model,data_kb,ext_kb,prefs_mtime,note" > "$OUT"
h(){ [ -z "$1" ] && echo "-" || printf %s "$1" | sha256sum | cut -c1-10; }

for i in "$@"; do
  name=$($LD list2 | tr -d '\r' | awk -F, -v i=$i '$1==i{print $2}')
  cfg=/d/LDPlayer/LDPlayer9/vms/config/leidian$i.config
  rootb=$(grep -oE '"basicSettings.rootMode":\s*(true|false)' $cfg | grep -oE 'true|false'); rootb=${rootb:-false}
  [ "$($LD isrunning --index $i | tr -d '\r')" = running ] && { echo "$i,$name,$rootb,,,,,,,,,,,,,,SKIP_RUNNING" >> "$OUT"; continue; }
  echo "== #$i $name: backup"
  f="$BK/$(echo "$name" | tr '/' '_')-inventory.ldbk"
  t0=$(date +%s); [ "${SKIPBK:-0}" = 1 ] || $LD backup --index $i --file "$(cygpath -w "$f")"; bs=$(( $(date +%s)-t0 ))
  bgb=$(awk -v b=$(stat -c %s "$f" 2>/dev/null || echo 0) 'BEGIN{printf "%.2f", b/1073741824}')
  [ "$bgb" = "0.00" ] && { echo "$i,$name,$rootb,0,$bs,,,,,,,,,,,,BACKUP_FAILED" >> "$OUT"; continue; }
  $LD modify --index $i --root 1; $LD launch --index $i
  S=emulator-$((5554 + 2*i))
  for _ in $(seq 1 60); do [ "$($ADB -s $S shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && break; sleep 3; done
  sleep 5
  ver=$($ADB -s $S shell "dumpsys package $P | grep versionName" 2>/dev/null | tr -d '\r ' | cut -d= -f2 | head -1)
  if [ -z "$ver" ]; then inst=no; else inst=yes; fi
  X=$($ADB -s $S shell "su -c 'cat /data/user/0/$P/shared_prefs/$P.v2.playerprefs.xml'" 2>/dev/null | tr -d '\r')
  get(){ echo "$X" | grep -oE "name=\"$1\"[^>]*>[^<]*<|name=\"$1\" value=\"[^\"]*\"" | head -1 | sed -E 's/.*value="([^"]*)".*/\1/; s/.*>([^<]*)<$/\1/'; }
  aid=$($ADB -s $S shell "su -c 'settings get secure android_id'" | tr -d '\r')
  model=$($ADB -s $S shell getprop ro.product.model | tr -d '\r')
  dkb=$($ADB -s $S shell "su -c 'du -sk /data/user/0/$P'" 2>/dev/null | tr -d '\r' | cut -f1)
  ekb=$($ADB -s $S shell "su -c 'du -sk /data/media/0/Android/data/$P'" 2>/dev/null | tr -d '\r' | cut -f1)
  mt=$($ADB -s $S shell "su -c 'stat -c %y /data/user/0/$P/shared_prefs/$P.v2.playerprefs.xml'" 2>/dev/null | tr -d '\r' | cut -c1-16)
  echo "$i,$name,$rootb,$bgb,$bs,$inst,$ver,$(h "$(get JOY_ACCOUNT_ID)"),$(h "$(get account_uuid)"),$(h "$(get game_uid)"),$(h "$(get device_uid)"),$(h "$aid"),$(h "$model"),$dkb,$ekb,$mt," >> "$OUT"
  $ADB -s $S shell "su -c 'cd /data/user/0/$P 2>/dev/null && du -sk * | sort -rn | head -4; cd /data/media/0/Android/data/$P 2>/dev/null && du -sk files/* 2>/dev/null | sort -rn | head -4'" | tr -d "" | sed "s/^/  #$i /" >> "$ROOT/logs/inventory_dirs.txt"
  $LD quit --index $i; sleep 5
  [ "$rootb" = false ] && $LD modify --index $i --root 0
  echo "== #$i done"
done
column -s, -t "$OUT"
