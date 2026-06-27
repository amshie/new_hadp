import type { KeyboardEvent } from "react";

// Keyboard-activation props for the VitaBahn screens' clickable <div> rows/cards
// (the comp used bare clickable divs; this restores the keyboard semantics the
// existing worklist already uses — role="button" + tabIndex + Enter/Space).
export function clickable(onActivate: () => void, label: string) {
  return {
    role: "button" as const,
    tabIndex: 0,
    "aria-label": label,
    onClick: onActivate,
    onKeyDown: (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onActivate();
      }
    },
  };
}
