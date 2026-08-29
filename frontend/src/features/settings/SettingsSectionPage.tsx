import { Navigate, useParams } from "react-router";

import { ApiKeysSection } from "./ApiKeysSection";
import { ChangelogSection } from "./ChangelogSection";
import { EmailSection } from "./EmailSection";
import { MonitoringSection } from "./MonitoringSection";
import { RequireRole } from "./SettingsLayout";
import { SignInSection } from "./SignInSection";
import { UsersSection } from "./UsersSection";
import { WebhooksSection } from "./WebhooksSection";

/** Maps the :section URL segment to a section component (AC-011). */
export function SettingsSectionPage() {
  const { section } = useParams();
  switch (section) {
    case "api-keys":
      return <ApiKeysSection />;
    case "webhooks":
      return (
        <RequireRole minimum="operator">
          <WebhooksSection />
        </RequireRole>
      );
    case "email":
      return (
        <RequireRole minimum="admin">
          <EmailSection />
        </RequireRole>
      );
    case "sign-in":
      return (
        <RequireRole minimum="admin">
          <SignInSection />
        </RequireRole>
      );
    case "monitoring":
      return (
        <RequireRole minimum="admin">
          <MonitoringSection />
        </RequireRole>
      );
    case "users":
      return (
        <RequireRole minimum="admin">
          <UsersSection />
        </RequireRole>
      );
    case "changelog":
      return <ChangelogSection />;
    default:
      return <Navigate to="/app/settings/api-keys" replace />;
  }
}
