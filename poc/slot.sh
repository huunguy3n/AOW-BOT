#!/usr/bin/env bash
# PoC Option C: snapshot / restore toan bo du lieu app (bit-for-bit, khong sua noi dung).
# Dung: slot.sh snapshot <name> | restore <name> | verify <name> | list
# Yeu cau: instance co root mode (LDPlayer), game DA DUNG khi ghi.
set -euo pipefail
export MSYS_NO_PATHCONV=1   # Git Bash: khong doi /data/... thanh duong dan Windows
w(){ cygpath -w "$1" 2>/dev/null || echo "$1"; }   # duong dan host cho adb.exe
ADB=${ADB:-/d/LDPlayer/LDPlayer9/adb.exe}
S=${S:-emulator-5568}
P=${P:-com.ageofwarpath.globalwarzone.vn}
U=${U:-0}
ROOT=$(cd "$(dirname "$0")" && pwd)
SLOTS="$ROOT/slots"; LOG="$ROOT/logs/slot.log"
DIRS="user/$U/$P user_de/$U/$P media/$U/Android/data/$P"   # relative to /data
TMP=/data/local/tmp/aow_slot

log(){ echo "$(date '+%F %T') [$1] ${*:2}" | tee -a "$LOG" >&2; }
sh_su(){ "$ADB" -s "$S" shell "su -c '$1'" | tr -d '\r'; }
now_ms(){ date +%s%3N; }

LOCKED=0
app_uid(){ "$ADB" -s "$S" shell "dumpsys package $P | grep userId=" 2>/dev/null | tr -d '\r' | grep -oE 'userId=[0-9]+' | head -1 | cut -d= -f2; }
procs_of_app(){  # moi tien trinh cua uid app (ke ca :service, process phu), khong chi theo ten
  local uid=$(( U*100000 + $(app_uid) ))
  "$ADB" -s "$S" shell "ps -A -o UID,PID,NAME" | tr -d '\r' | awk -v u=$uid '$1==u'
}
lock_app(){   # khoa package: launcher, FCM, alarm, job khong the khoi dong game trong luc ghi
  [ $LOCKED = 1 ] && return 0
  sh_su "pm disable-user --user $U $P" >/dev/null; LOCKED=1
  trap 'unlock_app' EXIT
}
unlock_app(){ [ $LOCKED = 1 ] && { sh_su "pm enable --user $U $P" >/dev/null; LOCKED=0; log INFO "unlock $P"; }; return 0; }

stop_game(){
  lock_app
  "$ADB" -s "$S" shell am force-stop "$P"
  for _ in $(seq 1 20); do
    [ -z "$(procs_of_app)" ] && return 0; sleep 0.5
  done
  log ERROR "game van chay sau force-stop: $(procs_of_app | tr '\n' ' ') -> ABORT"; exit 2
}

manifest(){  # sha256 cua moi file, duong dan tuong doi /data
  sh_su "cd /data && for d in $DIRS; do [ -d \$d ] && find \$d -type f; done | sort | while read f; do sha256sum \"\$f\"; done"
}

snapshot(){
  local name=$1 t0; t0=$(now_ms)
  stop_game
  mkdir -p "$SLOTS/$name.tmp"
  sh_su "rm -rf $TMP; mkdir -p $TMP; cd /data && tar -cpf $TMP/slot.tar --numeric-owner $DIRS"
  manifest > "$SLOTS/$name.tmp/manifest.sha256"
  "$ADB" -s "$S" pull "$TMP/slot.tar" "$(w "$SLOTS/$name.tmp/slot.tar")" >/dev/null
  sh_su "rm -rf $TMP"
  ( cd "$SLOTS/$name.tmp" && sha256sum slot.tar > slot.tar.sha256 )
  [ -d "$SLOTS/$name" ] && mv "$SLOTS/$name" "$SLOTS/$name.old.$(date +%s)"
  mv "$SLOTS/$name.tmp" "$SLOTS/$name"   # atomic tren cung o dia
  log OK "snapshot $name files=$(wc -l < "$SLOTS/$name/manifest.sha256") size=$(du -k "$SLOTS/$name/slot.tar"|cut -f1)KB ms=$(( $(now_ms)-t0 ))"
}

verify(){  # so manifest tren may voi manifest cua slot
  local name=$1
  if diff -q <(manifest) "$SLOTS/$name/manifest.sha256" >/dev/null; then log OK "verify $name: khop"; return 0
  else log FAIL "verify $name: KHONG khop"; diff <(manifest) "$SLOTS/$name/manifest.sha256" | head -20 >&2; return 1; fi
}

restore(){
  local name=$1 t0 ctx; t0=$(now_ms)
  [ -f "$SLOTS/$name/slot.tar" ] || { log ERROR "khong co slot $name"; exit 3; }
  ( cd "$SLOTS/$name" && sha256sum -c --quiet slot.tar.sha256 ) || { log ERROR "slot $name hong (checksum)"; exit 4; }
  stop_game
  local rb="_rollback_$(date +%Y%m%d_%H%M%S)"
  snapshot "$rb"                                  # luon backup truoc khi ghi de
  ctx=$(sh_su "ls -Zd /data/user/$U/$P" | awk '{print $1}')
  "$ADB" -s "$S" push "$(w "$SLOTS/$name/slot.tar")" "$TMP.tar" >/dev/null
  # xoa NOI DUNG (giu thu muc goc + uid/label cua no), giai nen, gan lai SELinux label
  sh_su "cd /data && for d in $DIRS; do [ -d \$d ] && find \$d -mindepth 1 -maxdepth 1 -exec rm -rf {} +; done; tar -xpf $TMP.tar -C /data; rm -f $TMP.tar; chcon -R $ctx /data/user/$U/$P /data/user_de/$U/$P; restorecon -R /data/media/$U/Android/data/$P"
  # Slot tu instance khac co the mang appId khac -> doi uid/gid (app, app_cache=+10000, ext=+20000)
  local src dst; src=$(tar -tvf "$SLOTS/$name/slot.tar" --numeric-owner 2>/dev/null | awk -v p="user/$U/$P/shared_prefs" 'index($NF,p){split($2,a,"/"); print a[1]; exit}')
  dst=$(app_uid)
  if [ -n "$src" ] && [ "$src" != "$dst" ]; then
    log INFO "remap uid $src -> $dst"
    sh_su "for o in 0 10000 20000; do s=\$(( $src + o )); t=\$(( $dst + o )); for d in /data/user/$U/$P /data/user_de/$U/$P /data/media/$U/Android/data/$P; do find \$d -uid \$s -exec chown -h \$t {} +; find \$d -gid \$s -exec chgrp -h \$t {} +; done; done"
  fi
  [ -z "$(procs_of_app)" ] || log WARN "co tien trinh app xuat hien trong luc restore!"
  if verify "$name"; then
    unlock_app
    log OK "restore $name ms=$(( $(now_ms)-t0 )) rollback=$rb"
  else
    log ERROR "restore $name loi -> ROLLBACK $rb"
    "$ADB" -s "$S" push "$(w "$SLOTS/$rb/slot.tar")" "$TMP.tar" >/dev/null
    sh_su "cd /data && for d in $DIRS; do [ -d \$d ] && find \$d -mindepth 1 -maxdepth 1 -exec rm -rf {} +; done; tar -xpf $TMP.tar -C /data; rm -f $TMP.tar; chcon -R $ctx /data/user/$U/$P /data/user_de/$U/$P"
    verify "$rb"; exit 5
  fi
}

case "${1:-}" in
  snapshot) snapshot "$2";; restore) restore "$2";; verify) verify "$2";;
  list) ls -1 "$SLOTS";; *) echo "usage: $0 snapshot|restore|verify <name> | list"; exit 1;;
esac
