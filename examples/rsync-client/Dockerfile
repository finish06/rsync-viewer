FROM alpine:3.21

RUN apk add --no-cache \
        rsync \
        openssh-client \
        curl \
        jq \
        flock \
        su-exec \
    && addgroup -S rsync \
    && adduser -S -G rsync -h /home/rsync rsync \
    && mkdir -p /data /scripts /home/rsync/.ssh \
    && chown -R rsync:rsync /data /home/rsync

COPY entrypoint.sh sync.sh /scripts/
RUN chmod +x /scripts/entrypoint.sh /scripts/sync.sh

VOLUME ["/data"]

ENTRYPOINT ["/scripts/entrypoint.sh"]
