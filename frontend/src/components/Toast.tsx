import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";

export type ToastKind = "success" | "error" | "info";

interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastApi {
  notify: (message: string, kind?: ToastKind) => void;
}

const ToastContext = createContext<ToastApi>({ notify: () => undefined });

const AUTO_DISMISS_MS = 4000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const notify = useCallback((message: string, kind: ToastKind = "success") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, kind, message }]);
    window.setTimeout(
      () => setToasts((t) => t.filter((x) => x.id !== id)),
      AUTO_DISMISS_MS,
    );
  }, []);

  const api = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-16 z-30 flex flex-col items-center gap-2 md:bottom-4"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            data-testid="toast"
            data-kind={toast.kind}
            className={`pointer-events-auto rounded-md border px-3 py-2 text-sm shadow-lg ${
              toast.kind === "error"
                ? "border-danger/50 bg-card text-danger"
                : toast.kind === "info"
                  ? "border-border bg-card text-text"
                  : "border-ok/50 bg-card text-ok"
            }`}
          >
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  return useContext(ToastContext);
}
