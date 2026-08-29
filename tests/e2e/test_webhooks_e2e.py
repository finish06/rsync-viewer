"""E2E tests for webhook management in the SPA — specs/settings-ui.md.

TC-002: create a Discord webhook with a colour, test it (mock URL → inline
failure, no stack trace), toggle it off, edit it, delete it. Plus a
client-side validation case for a non-Discord URL on a Discord webhook.
Screenshots: tests/screenshots/settings-ui/
"""

import uuid
from pathlib import Path

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL

SCREENSHOTS = (
    Path(__file__).resolve().parents[2] / "tests" / "screenshots" / "settings-ui"
)


def _shot(page: Page, name: str) -> None:
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENSHOTS / f"{name}.png"), full_page=True)


def _fake_discord_url() -> str:
    webhook_id = str(uuid.uuid4().int)[:18]
    token = uuid.uuid4().hex
    return f"https://discord.com/api/webhooks/{webhook_id}/{token}"


class TestWebhookLifecycle:
    def test_tc002_discord_webhook_test_toggle_edit_delete(self, admin_page: Page):
        admin_page.goto(f"{BASE_URL}/app/settings/webhooks")
        admin_page.wait_for_load_state("networkidle")

        section = admin_page.get_by_test_id("webhooks-section")
        expect(section).to_be_visible()
        section.get_by_role("button", name="+ Add webhook").click()

        form = admin_page.get_by_test_id("webhook-form")
        expect(form).to_be_visible()
        name = f"e2e-webhook-{uuid.uuid4().hex[:8]}"
        form.get_by_label("Name", exact=True).fill(name)
        form.get_by_label("Webhook type").select_option("discord")
        form.get_by_label("URL", exact=True).fill(_fake_discord_url())
        form.get_by_label("Embed colour").fill("#00ff88")
        form.get_by_label("Bot username").fill("E2E Bot")
        _shot(admin_page, "step-20-webhook-form")
        form.get_by_role("button", name="Save").click()

        row = admin_page.get_by_test_id("webhook-row").filter(has_text=name)
        expect(row).to_be_visible(timeout=10000)
        expect(row).to_have_attribute("data-status", "ok")
        expect(row).to_contain_text("discord")
        _shot(admin_page, "step-21-webhook-row")

        # Test delivery against a well-formed but unregistered Discord URL:
        # Discord answers fast with a non-2xx, so the API returns 502 and the
        # UI must show that inline — never a raw traceback.
        row.get_by_role("button", name="Test").click()
        alert = row.get_by_role("alert")
        expect(alert).to_be_visible(timeout=15000)
        alert_text = alert.text_content() or ""
        assert "Traceback" not in alert_text
        assert '  File "' not in alert_text

        # Toggle off — data-status flips and the button relabels.
        row.get_by_role("button", name="⏻ on").click()
        expect(row).to_have_attribute("data-status", "never", timeout=10000)
        expect(row.get_by_role("button", name="⏻ off")).to_be_visible()

        # Edit — rename and save.
        row.get_by_role("button", name="Edit").click()
        edit_form = row.get_by_test_id("webhook-form")
        expect(edit_form).to_be_visible()
        new_name = f"{name}-edited"
        edit_form.get_by_label("Name", exact=True).fill(new_name)
        edit_form.get_by_role("button", name="Save").click()

        edited_row = admin_page.get_by_test_id("webhook-row").filter(has_text=new_name)
        expect(edited_row).to_be_visible(timeout=10000)

        # Delete — arm then confirm.
        edited_row.get_by_role("button", name="Delete").click()
        edited_row.get_by_role("button", name="Confirm").click()
        expect(
            admin_page.get_by_test_id("webhook-row").filter(has_text=new_name)
        ).to_have_count(0, timeout=10000)

    def test_tc002_invalid_discord_url_shows_inline_validation_error(
        self, admin_page: Page
    ):
        admin_page.goto(f"{BASE_URL}/app/settings/webhooks")
        admin_page.wait_for_load_state("networkidle")
        section = admin_page.get_by_test_id("webhooks-section")
        section.get_by_role("button", name="+ Add webhook").click()

        form = admin_page.get_by_test_id("webhook-form")
        form.get_by_label("Name", exact=True).fill(
            f"e2e-invalid-{uuid.uuid4().hex[:8]}"
        )
        form.get_by_label("Webhook type").select_option("discord")
        form.get_by_label("URL", exact=True).fill(
            "https://example.com/not-a-discord-webhook"
        )
        form.get_by_role("button", name="Save").click()

        alert = form.get_by_role("alert")
        expect(alert).to_be_visible()
        expect(alert).to_contain_text("Discord webhooks need a URL")

        form.get_by_role("button", name="Cancel").click()
        expect(admin_page.get_by_test_id("webhook-form")).to_have_count(0)
