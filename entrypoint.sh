#!/bin/sh
# Auto-generate ENCRYPTION_KEY if not provided
if [ -z "$ENCRYPTION_KEY" ] && [ -z "$SMTP_ENCRYPTION_KEY" ]; then
    export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    echo "INFO: Auto-generated ENCRYPTION_KEY (set explicitly in production for persistence)"
fi

exec "$@"
