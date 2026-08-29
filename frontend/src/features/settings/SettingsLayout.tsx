import { Navigate, NavLink, Outlet, useLocation } from "react-router";

import { currentUser, hasRole, type Role } from "../../app/user";

export interface SettingsSection {
  slug: string;
  label: string;
  minRole?: Role;
}

// Order = how often people need them (spec principle: settings are secondary).
export const SECTIONS: SettingsSection[] = [
  { slug: "api-keys", label: "API keys" },
  { slug: "webhooks", label: "Webhooks", minRole: "operator" },
  { slug: "email", label: "Email", minRole: "admin" },
  { slug: "sign-in", label: "Sign-in", minRole: "admin" },
  { slug: "monitoring", label: "Monitoring", minRole: "admin" },
  { slug: "users", label: "Users", minRole: "admin" },
  { slug: "changelog", label: "Changelog" },
];

export function visibleSections(): SettingsSection[] {
  const user = currentUser();
  return SECTIONS.filter(
    (s) => !s.minRole || !user || hasRole(user, s.minRole),
  );
}

export function SettingsLayout() {
  const sections = visibleSections();
  return (
    <div
      className="grid gap-4 md:grid-cols-[12rem_1fr]"
      data-testid="settings-layout"
    >
      <nav
        aria-label="Settings"
        className="card p-2 md:sticky md:top-16 md:self-start"
      >
        <p className="px-2 pb-1 text-xs font-semibold uppercase tracking-wider text-muted">
          Settings
        </p>
        <ul className="flex gap-1 overflow-x-auto md:flex-col">
          {sections.map((section) => (
            <li key={section.slug}>
              <NavLink
                to={`/app/settings/${section.slug}`}
                className={({ isActive }) =>
                  `block whitespace-nowrap rounded-md px-2 py-1.5 text-sm ${
                    isActive
                      ? "bg-bg-secondary font-medium text-text"
                      : "text-muted hover:text-text"
                  }`
                }
              >
                {section.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="min-w-0">
        <Outlet />
      </div>
    </div>
  );
}

/** `/app/settings` lands on API keys; legacy `/settings#changelog` links keep working. */
export function SettingsIndex() {
  const { hash } = useLocation();
  const section = hash === "#changelog" ? "changelog" : "api-keys";
  return <Navigate to={`/app/settings/${section}`} replace />;
}

/** Guard for direct links to admin-only sections. */
export function RequireRole({
  minimum,
  children,
}: {
  minimum: Role;
  children: React.ReactNode;
}) {
  const user = currentUser();
  if (user && !hasRole(user, minimum)) {
    return (
      <div className="card p-4 text-sm text-muted" data-testid="forbidden">
        You need the <b>{minimum}</b> role for this section.
      </div>
    );
  }
  return <>{children}</>;
}
