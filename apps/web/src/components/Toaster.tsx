"use client";

import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { Icon } from "./Icon";

type Tone = "default" | "success";
type ToastItem = { id: number; message: string; tone: Tone; leaving: boolean };

type Toast = (message: string, tone?: Tone) => void;

// No provider, no toast: a page that shows its actions' errors this way must not lose them to
// a silent default (it did once, when the review page left the shell that provided one).
const ToastContext = createContext<Toast | null>(null);

export function useToast(): Toast {
  const toast = useContext(ToastContext);
  if (toast === null) {
    throw new Error("useToast() needs a <ToastProvider> around the component");
  }
  return toast;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const toast = useCallback((message: string, tone: Tone = "default") => {
    const id = nextId.current++;
    setItems((prev) => [...prev, { id, message, tone, leaving: false }]);
    // Mirror the prototype: visible ~3200ms, then a short fade before removal.
    window.setTimeout(() => {
      setItems((prev) =>
        prev.map((t) => (t.id === id ? { ...t, leaving: true } : t)),
      );
      window.setTimeout(
        () => setItems((prev) => prev.filter((t) => t.id !== id)),
        190,
      );
    }, 3200);
  }, []);

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="toast-region" aria-live="polite" aria-atomic="true">
        {items.map((t) => (
          <div
            key={t.id}
            className={`toast${t.tone === "success" ? " success" : ""}`}
            style={
              t.leaving
                ? { opacity: 0, transform: "translateY(8px)" }
                : undefined
            }
          >
            <Icon name={t.tone === "success" ? "check" : "alert"} />
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
