#!/bin/sh
set -eu

# Generate host keys if missing
ssh-keygen -A

# Install the public key from the shared volume
if [ -f /ssh-keys/id_rsa.pub ]; then
    cp /ssh-keys/id_rsa.pub /home/testuser/.ssh/authorized_keys
    chown testuser:testuser /home/testuser/.ssh/authorized_keys
    chmod 600 /home/testuser/.ssh/authorized_keys
    echo "Installed authorized_keys for testuser"
else
    echo "ERROR: /ssh-keys/id_rsa.pub not found" >&2
    exit 1
fi

# Ensure password auth is off (key-only)
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
# Allow the testuser
echo "AllowUsers testuser" >> /etc/ssh/sshd_config

echo "Starting sshd..."
exec /usr/sbin/sshd -D -e
