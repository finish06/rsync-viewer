import { useState } from "react";

import { useUserMutations, useUsers } from "../../api/hooks";
import type { UserRead } from "../../api/types";
import { currentUser } from "../../app/user";
import { EmptyNote, ErrorCard, Panel, Skeleton } from "../../components/Panel";
import { useToast } from "../../components/Toast";
import { formatRelative } from "../../lib/format";
import {
  ConfirmButton,
  errorMessage,
  inputClass,
  SecondaryButton,
} from "./FormBits";

const ROLES: UserRead["role"][] = ["viewer", "operator", "admin"];

export function UsersSection() {
  const me = currentUser();
  const users = useUsers();
  const { changeRole, changeStatus, remove, resetPassword } =
    useUserMutations();
  const toast = useToast();
  const [armed, setArmed] = useState<string | null>(null);
  const [rowError, setRowError] = useState<{
    id: string;
    message: string;
  } | null>(null);

  function run<T>(id: string, promise: Promise<T>, success: string) {
    setRowError(null);
    promise
      .then(() => toast.notify(success))
      .catch((error: unknown) =>
        setRowError({ id, message: errorMessage(error) }),
      );
  }

  return (
    <Panel title="Users" testId="users-section">
      {users.isPending && <Skeleton className="h-24" />}
      {users.isError && (
        <ErrorCard
          message="Could not load users."
          onRetry={() => void users.refetch()}
        />
      )}
      {users.isSuccess && users.data.length === 0 && (
        <EmptyNote>No users.</EmptyNote>
      )}
      {users.isSuccess && users.data.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wider text-muted">
              <tr>
                <th className="py-1 pr-3">username</th>
                <th className="py-1 pr-3">email</th>
                <th className="py-1 pr-3">role</th>
                <th className="py-1 pr-3">status</th>
                <th className="py-1 pr-3">last login</th>
                <th className="py-1" />
              </tr>
            </thead>
            <tbody>
              {users.data.map((user) => {
                const self = me?.username === user.username;
                return (
                  <tr
                    key={user.id}
                    data-testid="user-row"
                    className="border-t border-border align-top"
                  >
                    <td className="py-1.5 pr-3 font-medium">
                      {user.username}
                      {self && (
                        <span className="ml-1 text-xs text-muted">(you)</span>
                      )}
                    </td>
                    <td className="py-1.5 pr-3 text-muted">{user.email}</td>
                    <td className="py-1.5 pr-3">
                      {self ? (
                        user.role
                      ) : (
                        <select
                          aria-label={`Role for ${user.username}`}
                          className={inputClass}
                          value={user.role}
                          onChange={(e) =>
                            run(
                              user.id,
                              changeRole.mutateAsync({
                                id: user.id,
                                role: e.target.value as UserRead["role"],
                              }),
                              `${user.username} is now ${e.target.value}`,
                            )
                          }
                        >
                          {ROLES.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td className="py-1.5 pr-3">
                      <span
                        data-status={user.is_active ? "ok" : "never"}
                        className="inline-flex items-center gap-1"
                      >
                        <span
                          className="h-2 w-2 rounded-full"
                          style={{ background: "var(--status)" }}
                          aria-hidden
                        />
                        {user.is_active ? "active" : "disabled"}
                      </span>
                    </td>
                    <td className="py-1.5 pr-3 text-muted">
                      {formatRelative(user.last_login_at)}
                    </td>
                    <td className="py-1.5">
                      {!self && (
                        <div className="flex flex-wrap justify-end gap-1">
                          <SecondaryButton
                            onClick={() =>
                              run(
                                user.id,
                                changeStatus.mutateAsync({
                                  id: user.id,
                                  is_active: !user.is_active,
                                }),
                                `${user.username} ${user.is_active ? "disabled" : "enabled"}`,
                              )
                            }
                          >
                            {user.is_active ? "Disable" : "Enable"}
                          </SecondaryButton>
                          <SecondaryButton
                            onClick={() =>
                              run(
                                user.id,
                                resetPassword.mutateAsync(user.id),
                                `Password reset sent to ${user.email}`,
                              )
                            }
                          >
                            Reset password
                          </SecondaryButton>
                          <ConfirmButton
                            label="Delete"
                            confirmLabel="Delete user"
                            armed={armed === user.id}
                            onArm={() => setArmed(user.id)}
                            onCancel={() => setArmed(null)}
                            busy={remove.isPending}
                            onConfirm={() => {
                              run(
                                user.id,
                                remove.mutateAsync(user.id),
                                `${user.username} deleted`,
                              );
                              setArmed(null);
                            }}
                          />
                        </div>
                      )}
                      {rowError?.id === user.id && (
                        <p
                          role="alert"
                          className="mt-1 text-right text-xs text-danger"
                        >
                          {rowError.message}
                        </p>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
