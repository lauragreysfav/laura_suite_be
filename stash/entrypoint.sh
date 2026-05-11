#!/bin/bash
set -e

mkdir -p /data/torbox
nohup rclone mount torbox: /data/torbox \
  --allow-non-empty \
  --allow-other \
  --vfs-cache-mode writes \
  --dir-cache-time 30s \
  --config /etc/rclone.conf \
  > /dev/null 2>&1 &

for i in $(seq 1 15); do
  if ls /data/torbox/ >/dev/null 2>&1; then
    echo "TorBox WebDAV mounted at /data/torbox"
    break
  fi
  sleep 1
done

exec /usr/local/bin/original-entrypoint.sh "$@"
