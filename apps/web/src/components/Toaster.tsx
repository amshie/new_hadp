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

const ToastContext = createContext<(message: string, tone?: Tone) => void>(
  () => {},
);

export function useToast() {
  return useContext(ToastContext);
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
