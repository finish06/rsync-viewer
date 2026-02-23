"""Tests for settings page and dark mode theme feature.

Spec: specs/dark-mode.md
"""


class TestSettingsPage:
    """Test GET /settings endpoint — AC-007, AC-008, AC-010"""

    async def test_ac007_settings_page_returns_200(self, client):
        """AC-007: A settings page exists at /settings"""
        response = await client.get("/settings")
        assert response.status_code == 200

    async def test_ac007_settings_page_contains_theme_options(self, client):
        """AC-007: Settings page has theme toggle with light/dark/system"""
        response = await client.get("/settings")
        html = response.text
        assert "Light" in html
        assert "Dark" in html
        assert "System" in html

    async def test_ac010_settings_page_has_appearance_section(self, client):
        """AC-010: Settings page structured for future settings sections"""
        response = await client.get("/settings")
        html = response.text
        assert "Appearance" in html or "Theme" in html

    async def test_ac008_header_has_settings_link(self, client):
        """AC-008: Settings page is navigable from the header"""
        response = await client.get("/")
        html = response.text
        assert "/settings" in html


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
