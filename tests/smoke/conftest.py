# Standalone conftest for smoke tests.
# Prevents pytest from loading the root tests/conftest.py which
# imports the full app stack (jwt, sqlmodel, fastapi, etc.).
