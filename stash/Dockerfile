FROM nerethos/stash:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    rclone fuse3 cmake g++ build-essential python3-dev && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /data/torbox

COPY rclone.conf /etc/rclone.conf
COPY entrypoint.sh /entrypoint-wrapper.sh
RUN chmod +x /entrypoint-wrapper.sh && \
    mv /usr/local/bin/entrypoint.sh /usr/local/bin/original-entrypoint.sh

ENTRYPOINT ["/entrypoint-wrapper.sh"]
