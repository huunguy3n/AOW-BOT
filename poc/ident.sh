#!/usr/bin/env bash
# In danh tinh tai khoan duoi dang hash ngan (khong lo gia tri that)
export MSYS_NO_PATHCONV=1; ADB=${ADB:-/d/LDPlayer/LDPlayer9/adb.exe}; S=${S:-emulator-5568}; P=com.ageofwarpath.globalwarzone.vn; U=${U:-0}
X=$($ADB -s $S shell "su -c 'cat /data/user/$U/$P/shared_prefs/$P.v2.playerprefs.xml'" 2>/dev/null | tr -d '\r')
for k in JOY_ACCOUNT_ID JOY_ACCOUNT_UNAME account_uuid game_uid NEW_GAMEUID device_uid bindType; do
  v=$(echo "$X" | grep -oE "name=\"$k\"[^>]*>[^<]*<|name=\"$k\" value=\"[^\"]*\"" | head -1 | sed -E 's/.*value="([^"]*)".*/\1/; s/.*>([^<]*)<$/\1/')
  if [ -z "$v" ]; then h="(none)"; else h=$(printf '%s' "$v" | sha256sum | cut -c1-10); fi
  printf '%-18s %s\n' "$k" "$h"
done
