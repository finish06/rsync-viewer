FROM alpine:3.21

RUN apk add --no-cache openssh-server rsync \
    && adduser -D -s /bin/sh testuser \
    && passwd -u testuser \
    && mkdir -p /home/testuser/.ssh \
    && chown testuser:testuser /home/testuser/.ssh \
    && chmod 700 /home/testuser/.ssh \
    && mkdir -p /test-data \
    && chown testuser:testuser /test-data

# Create test data: 2 text files + 1 64KB binary
RUN echo "Hello from the e2e rsync test server" > /test-data/readme.txt \
    && echo "second file for transfer count" > /test-data/notes.txt \
    && dd if=/dev/urandom of=/test-data/sample.bin bs=1024 count=64 2>/dev/null \
    && chown -R testuser:testuser /test-data

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22

ENTRYPOINT ["/entrypoint.sh"]
