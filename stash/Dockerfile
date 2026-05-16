FROM nerethos/stash:latest

RUN apt-get update && apt-get install -y --no-install-recommends rclone fuse3 && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /data/torbox

COPY rclone.conf /etc/rclone.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
