import { patientView } from "@/lib/api";

export default async function PatientViewPage({
  searchParams,
}: {
  searchParams: Promise<{ tenant?: string; token?: string }>;
}) {
  const { tenant, token } = await searchParams;
  if (!tenant || !token) {
    return <p>Invalid link.</p>;
  }
  try {
    const view = await patientView(tenant, token);
    return (
      <div>
        <h1>Your report</h1>
        <p className="muted">
          Released {view.released_at ? view.released_at.slice(0, 10) : ""} ·
          synthetic demo content
        </p>
        <p className="muted">
          This summary reflects your laboratory results and the reference ranges
          your laboratory provided. It is not a diagnosis or treatment advice.
          Please discuss it with your clinician.
        </p>
        {view.statements.map((s) => (
          <div key={s.id} className="card">
            <p>{s.text}</p>
          </div>
        ))}
      </div>
    );
  } catch {
    // Do not reveal whether the link is wrong, expired, or unreleased.
    return <p>This report is not available.</p>;
  }
}
