"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { byCount } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";

import { endOtherSessionsAction } from "./actions";

// "Alle anderen Sitzungen beenden": asks first, then says how many ended.
export function EndOthers({ others }: { others: number }) {
  const router = useRouter();
  const t = useI18n().t.securityPage.sessions;
  const [message, setMessage] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const end = () => {
    if (!window.confirm(t.endConfirm)) return;
    startTransition(async () => {
      const res = await endOtherSessionsAction();
      setMessage(res.ok ? byCount(t.ended, res.ended) : t.failed);
      router.refresh();
    });
  };

  return (
    <div className="vb-sec-end">
      {others > 0 ? (
        <button
          type="button"
          className="vb-ov-btn"
          disabled={pending}
          onClick={end}
        >
          {t.endOthers}
        </button>
      ) : (
        <span className="vb-ov-note" style={{ margin: 0 }}>
          {t.none}
        </span>
      )}
      <span role="status" className="vb-ov-note" style={{ margin: 0 }}>
        {message}
      </span>
    </div>
  );
}
