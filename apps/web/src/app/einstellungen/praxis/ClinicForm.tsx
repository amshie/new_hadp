"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { useI18n } from "@/lib/i18n/I18nProvider";

import { saveClinicProfileAction } from "./actions";

// The owner's form for the clinic's name and address.
export function ClinicForm({
  name,
  address,
}: {
  name: string;
  address: string | null;
}) {
  const router = useRouter();
  const t = useI18n().t.clinicPage;
  const [values, setValues] = useState({ name, address: address ?? "" });
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(
    null,
  );
  const [pending, startTransition] = useTransition();

  return (
    <form
      className="vb-clinic-form"
      onSubmit={(e) => {
        e.preventDefault();
        startTransition(async () => {
          const res = await saveClinicProfileAction(
            values.name,
            values.address,
          );
          setMessage(
            res.ok
              ? { ok: true, text: t.saved }
              : { ok: false, text: t.errors[res.error] },
          );
          if (res.ok) router.refresh();
        });
      }}
    >
      <div className="vb-team-field">
        <label htmlFor="clinic-name">{t.name}</label>
        <input
          id="clinic-name"
          type="text"
          required
          maxLength={200}
          value={values.name}
          onChange={(e) => setValues({ ...values, name: e.target.value })}
        />
      </div>
      <div className="vb-team-field">
        <label htmlFor="clinic-address">{t.address}</label>
        <textarea
          id="clinic-address"
          rows={3}
          maxLength={300}
          value={values.address}
          aria-describedby="clinic-address-help"
          onChange={(e) => setValues({ ...values, address: e.target.value })}
        />
        <small id="clinic-address-help">{t.addressHelp}</small>
      </div>
      <div className="vb-sec-end">
        <button type="submit" className="vb-ov-btn primary" disabled={pending}>
          {t.save}
        </button>
        <span
          role={message && !message.ok ? "alert" : "status"}
          className="vb-ov-note"
          style={{ margin: 0 }}
        >
          {message?.text}
        </span>
      </div>
    </form>
  );
}
