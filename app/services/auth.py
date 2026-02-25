import bcrypt


# Role constants
ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
ROLE_VIEWER = "viewer"

VALID_ROLES = {ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER}

# Role hierarchy: higher index = more permissions
ROLE_HIERARCHY = {
    ROLE_VIEWER: 0,
    ROLE_OPERATOR: 1,
    ROLE_ADMIN: 2,
}

# Permission matrix: resource -> minimum role required
PERMISSIONS = {
    "view_dashboard": ROLE_VIEWER,
    "view_sync_logs": ROLE_VIEWER,
    "submit_sync_logs": ROLE_OPERATOR,
    "view_webhooks": ROLE_VIEWER,
    "manage_webhooks": ROLE_OPERATOR,
    "delete_sync_logs": ROLE_ADMIN,
    "manage_users": ROLE_ADMIN,
    "view_settings": ROLE_OPERATOR,
    "manage_own_api_keys": ROLE_VIEWER,
    "manage_all_api_keys": ROLE_ADMIN,
}


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def has_permission(user_role: str, permission: str) -> bool:
    """Check if a role has a given permission."""
    required_role = PERMISSIONS.get(permission)
    if required_role is None:
        return False
    return ROLE_HIERARCHY.get(user_role, -1) >= ROLE_HIERARCHY.get(required_role, 999)


def role_at_least(user_role: str, minimum_role: str) -> bool:
    """Check if user_role is at or above minimum_role in hierarchy."""
    return ROLE_HIERARCHY.get(user_role, -1) >= ROLE_HIERARCHY.get(minimum_role, 999)
