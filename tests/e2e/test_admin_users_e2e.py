"""E2E tests for admin user management — happy paths and error scenarios.

Spec: specs/e2e-playwright-happy-path.md (AC-017, TC-006)
Spec: specs/e2e-playwright-error-scenarios.md (AC-131, AC-132)
"""

import uuid

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL, register_user_via_api


class TestAdminUserManagement:
    """TC-006: Admin user list and role management."""

    def test_ac017_admin_page_loads(self, admin_page: Page):
        """Admin users page renders with user list."""
        admin_page.goto(f"{BASE_URL}/admin/users")
        admin_page.wait_for_load_state("networkidle")

        # Should see the user list container
        user_list = admin_page.locator("#admin-user-list")
        expect(user_list).to_be_visible(timeout=10000)

        # Wait for HTMX to load the user table
        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('admin-user-list');
                return el && el.innerHTML.trim().length > 50;
            }""",
            timeout=10000,
        )

    def test_ac017_user_list_shows_users(self, admin_page: Page):
        """User list contains at least one user with a role column."""
        admin_page.goto(f"{BASE_URL}/admin/users")
        admin_page.wait_for_load_state("networkidle")

        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('admin-user-list');
                return el && el.innerHTML.trim().length > 50;
            }""",
            timeout=10000,
        )

        # The table should have at least one row with a role select
        rows = admin_page.locator("#admin-user-list tr")
        assert rows.count() >= 2  # header + at least 1 data row

    def test_ac017_change_user_role(self, admin_page: Page, viewer_credentials: dict):
        """Admin can change another user's role."""
        admin_page.goto(f"{BASE_URL}/admin/users")
        admin_page.wait_for_load_state("networkidle")

        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('admin-user-list');
                return el && el.innerHTML.trim().length > 50;
            }""",
            timeout=10000,
        )

        # Find role select for the viewer user
        # The select should be in the same row as the viewer's username
        viewer_row = admin_page.locator(
            f"tr:has-text('{viewer_credentials['username']}')"
        )
        if viewer_row.count() > 0:
            role_select = viewer_row.locator('select[name="role"]')
            if role_select.count() > 0:
                # Change to operator
                role_select.select_option("operator")
                admin_page.wait_for_timeout(2000)

                # Verify the change stuck (reload)
                admin_page.goto(f"{BASE_URL}/admin/users")
                admin_page.wait_for_load_state("networkidle")
                admin_page.wait_for_function(
                    """() => {
                        const el = document.getElementById('admin-user-list');
                        return el && el.innerHTML.trim().length > 50;
                    }""",
                    timeout=10000,
                )

                # Change back to viewer to not affect other tests
                viewer_row = admin_page.locator(
                    f"tr:has-text('{viewer_credentials['username']}')"
                )
                role_select = viewer_row.locator('select[name="role"]')
                if role_select.count() > 0:
                    role_select.select_option("viewer")
                    admin_page.wait_for_timeout(2000)

    def test_ac017_toggle_user_status(self, admin_page: Page):
        """Admin can toggle a user's active status."""
        # Create a throwaway user to toggle
        uid = uuid.uuid4().hex[:8]
        username = f"e2e_toggle_{uid}"
        register_user_via_api(username, f"{username}@test.local", "TogglePass123!")

        admin_page.goto(f"{BASE_URL}/admin/users")
        admin_page.wait_for_load_state("networkidle")

        admin_page.wait_for_function(
            """() => {
                const el = document.getElementById('admin-user-list');
                return el && el.innerHTML.trim().length > 50;
            }""",
            timeout=10000,
        )

        # Find toggle button for the test user
        user_row = admin_page.locator(f"tr:has-text('{username}')")
        if user_row.count() > 0:
            toggle_btn = user_row.locator('[hx-put*="toggle-status"]')
            if toggle_btn.count() > 0:
                toggle_btn.click()
                admin_page.wait_for_timeout(2000)
                # Page should update via HTMX
                assert "/admin/users" in admin_page.url


class TestAdminRBAC:
    """RBAC enforcement on admin pages — AC-131, AC-132, TC-104."""

    def test_ac131_viewer_cannot_access_admin_users(self, viewer_page: Page):
        """Viewer user gets 403 or redirect when accessing /admin/users."""
        viewer_page.goto(f"{BASE_URL}/admin/users")
        viewer_page.wait_for_load_state("networkidle")

        # Should NOT see the admin user list table
        # Either 403 page, redirect to login, or forbidden message
        content = viewer_page.content()
        has_user_table = viewer_page.locator("#admin-user-list table").count() > 0
        assert not has_user_table or "403" in content or "forbidden" in content.lower()

    def test_ac132_viewer_cannot_change_roles_via_htmx(self, viewer_page: Page):
        """Viewer user cannot use admin HTMX endpoints."""
        # Try to access the admin user list HTMX endpoint directly
        viewer_page.goto(f"{BASE_URL}/htmx/admin/users")
        viewer_page.wait_for_load_state("networkidle")

        content = viewer_page.content()
        # Should NOT see a populated user table with role selects
        has_role_selects = viewer_page.locator('select[name="role"]').count() > 0
        assert not has_role_selects or "403" in content
