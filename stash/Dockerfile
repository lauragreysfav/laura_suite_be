FROM nerethos/stash:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    rclone fuse3 cmake g++ build-essential python3-dev && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /data/torbox

COPY requirements.txt /tmp/stash-requirements.txt
RUN python3 -m pip install --break-system-packages \
    apscheduler==3.11.2 \
    stashapp-tools==0.2.59 \
    thefuzz==0.22.1 \
    dateparser==1.4.0 \
    python-levenshtein==0.27.3 \
    requests==2.33.1 && \
    rm /tmp/stash-requirements.txt

COPY rclone.conf /etc/rclone.conf
COPY entrypoint.sh /entrypoint-wrapper.sh
RUN chmod +x /entrypoint-wrapper.sh && \
    mv /usr/local/bin/entrypoint.sh /usr/local/bin/original-entrypoint.sh

ENTRYPOINT ["/entrypoint-wrapper.sh"]
