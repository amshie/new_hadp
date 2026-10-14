import type { AuditStepView } from "@/lib/presenters/review";

// The report's audit steps, from the presenter (lib/presenters/review): the same stepper on
// the patient page and on the report page. Each step shows its number, or a check once it is
// done, its label and the line that fits its state; the page hands in the wording in its
// language. The list needs 560px and scrolls sideways on a narrower screen.
export function AuditSteps({
  steps,
  copy,
}: {
  steps: AuditStepView[];
  copy: Record<string, Record<string, string>>;
}) {
  return (
    <div className="vb-audit-scroll">
      <ol className="vb-audit-steps">
        {steps.map((s) => {
          const step = copy[s.key] ?? {};
          const state =
            s.state === "done"
              ? " is-done"
              : s.state === "active"
                ? " is-active"
                : "";
          return (
            <li
              key={s.key}
              className={`vb-audit-step${state}`}
              aria-current={s.state === "active" ? "step" : undefined}
            >
              <span className="vb-audit-step-track">
                <span className="vb-audit-step-dot">
                  {s.state === "done" ? (
                    <svg
                      aria-hidden="true"
                      focusable="false"
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                  ) : (
                    s.dot
                  )}
                </span>
              </span>
              <span className="vb-audit-step-label">{step.label}</span>
              <span className="vb-audit-step-sub">{step[s.subKey] ?? ""}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
