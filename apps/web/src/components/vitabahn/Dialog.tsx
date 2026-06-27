"use client";

import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";

// Shared accessible modal primitive for the VitaBahn surfaces. Centralizes the WCAG 2.2 modal
// behavior first written for AddPatientDialog so every modal behaves the same:
//   • role="dialog" + aria-modal + aria-labelledby (and optional aria-describedby)
//   • Escape closes
//   • focus moves into the dialog on open (an explicit target, else the first focusable)
//   • focus is restored to whatever was focused before opening (the trigger) on close
//   • a Tab / Shift+Tab focus trap keeps keyboard focus inside the aria-modal dialog
//   • a backdrop click closes (mousedown on the backdrop itself, so a drag that ends outside
//     does not close)
// Styling stays with the caller — pass VitaBahn token styles via style props, or class names for
// surfaces that use CSS classes (e.g. the HADP review dialog). Only the behavior is shared here.
//
// Render the dialog conditionally (`{open && <Dialog …>}`) so it mounts on open and unmounts on
// close; the focus capture/restore is keyed to that mount lifecycle.

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

// Structural, covariant ref type so any `useRef<HTMLInputElement>()` / `<HTMLButtonElement>()` is
// accepted (React 19's RefObject.current is mutable, hence invariant — a readonly current is not).
type FocusRef = { readonly current: HTMLElement | null };

export function Dialog({
  onClose,
  labelledBy,
  describedBy,
  initialFocusRef,
  closeOnBackdrop = true,
  lockScroll = false,
  backdropStyle,
  backdropClassName,
  dialogStyle,
  dialogClassName,
  children,
}: {
  onClose: () => void;
  labelledBy: string;
  describedBy?: string;
  initialFocusRef?: FocusRef;
  closeOnBackdrop?: boolean;
  lockScroll?: boolean;
  backdropStyle?: CSSProperties;
  backdropClassName?: string;
  dialogStyle?: CSSProperties;
  dialogClassName?: string;
  children: ReactNode;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Captured before focus moves in, so it points at the trigger (a button, or a clickable row)
    // and can be restored on close. Read once on mount; nothing moves focus before this runs.
    const trigger = document.activeElement as HTMLElement | null;
    if (lockScroll) document.body.classList.add("modal-open");

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "Tab") {
        const dlg = dialogRef.current;
        if (!dlg) return;
        const list = Array.from(
          dlg.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
        );
        const first = list[0];
        const last = list[list.length - 1];
        if (!first || !last) return;
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", onKey);

    const t = window.setTimeout(() => {
      const target =
        initialFocusRef?.current ??
        dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR) ??
        null;
      target?.focus();
    }, 30);

    return () => {
      window.removeEventListener("keydown", onKey);
      window.clearTimeout(t);
      if (lockScroll) document.body.classList.remove("modal-open");
      trigger?.focus?.();
    };
    // Mount/unmount only — the dialog is conditionally rendered, so open/close maps to it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      role="presentation"
      className={backdropClassName}
      onMouseDown={(e) => {
        if (closeOnBackdrop && e.target === e.currentTarget) onClose();
      }}
      style={backdropStyle}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        className={dialogClassName}
        style={dialogStyle}
      >
        {children}
      </div>
    </div>
  );
}
