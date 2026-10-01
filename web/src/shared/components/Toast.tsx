import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import clsx from "clsx";
import { useErrorMessage } from "../hooks/useErrorMessage";

type Tone = "success" | "error";
interface ToastItem {
  id: number;
  tone: Tone;
  message: string;
}

interface ToastApi {
  success: (message: string) => void;
  error: (errorOrMessage: unknown) => void;
}

const ToastContext = createContext<ToastApi | null>(null);
let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const toMessage = useErrorMessage();

  const push = useCallback((tone: Tone, message: string) => {
    const id = nextId++;
    setItems((prev) => [...prev.slice(-2), { id, tone, message }]);
    window.setTimeout(() => setItems((prev) => prev.filter((t) => t.id !== id)), tone === "error" ? 6000 : 3500);
  }, []);

  const api = useMemo<ToastApi>(
    () => ({
      success: (message) => push("success", message),
      error: (e) => push("error", typeof e === "string" ? e : toMessage(e)),
    }),
    [push, toMessage],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toast-region" aria-live="polite">
        {items.map((item) => (
          <div key={item.id} className={clsx("toast", `toast-${item.tone}`)} role={item.tone === "error" ? "alert" : "status"}>
            {item.tone === "success" ? <CheckCircle2 aria-hidden /> : <AlertCircle aria-hidden />}
            <span>{item.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}
