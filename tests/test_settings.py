"""Tests for settings page and dark mode theme feature.

Spec: specs/dark-mode.md
"""

import pytest


class TestSettingsPage:
    """GET /settings now redirects into the SPA (specs/settings-ui.md AC-020)."""

    @pytest.mark.anyio
    async def test_ac020_settings_redirects_to_spa(self, client):
        response = await client.get("/settings", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/app/settings"

    @pytest.mark.anyio
    async def test_ac020_admin_users_redirects_to_spa(self, client):
        response = await client.get("/admin/users", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/app/settings/users"


class TestThemeCSS:
    """Test that dark theme CSS variables are defined — AC-001, AC-003"""

    async def test_ac001_dark_theme_css_exists(self, client):
        """AC-001: Dark theme CSS overrides are defined"""
        response = await client.get("/static/css/styles.css")
        css = response.text
        assert '[data-theme="dark"]' in css

    async def test_ac003_dark_theme_defines_bg_color(self, client):
        """AC-003: Dark theme provides dark background"""
        response = await client.get("/static/css/styles.css")
        css = response.text
        assert "--bg-color" in css
        # Dark bg color should be present
        assert "#111827" in css

    async def test_ac002_light_theme_preserved(self, client):
        """AC-002: Light theme matches existing appearance (CSS vars in :root)"""
        response = await client.get("/static/css/styles.css")
        css = response.text
        # Existing light theme values should still be in :root
        assert "#f9fafb" in css
        assert "#ffffff" in css


class TestThemeJavaScript:
    """Test that theme JavaScript is loaded — AC-005, AC-011"""

    async def test_ac005_theme_js_loaded(self, client):
        """AC-005: Theme JS is included in the page"""
        response = await client.get("/")
        html = response.text
        assert "theme" in html.lower()

    async def test_ac011_fouc_prevention_script(self, client):
        """AC-011: Inline FOUC prevention script in <head>"""
        response = await client.get("/")
        html = response.text
        head_section = html.split("</head>")[0] if "</head>" in html else html
        assert "localStorage" in head_section
        assert "data-theme" in head_section

    async def test_ac005_theme_js_file_exists(self, client):
        """AC-005: theme.js static file is servable"""
        response = await client.get("/static/js/theme.js")
        assert response.status_code == 200
