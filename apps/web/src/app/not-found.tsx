import Link from "next/link";

import { BrandMark } from "@/components/vitabahn/BrandMark";
import { PublicScope } from "@/components/vitabahn/PublicScope";
import { getMessages } from "@/lib/i18n/server";

// Neutral 404 for unknown routes and notFound() throws — no route details echoed.
export default async function NotFound() {
  const t = (await getMessages()).notFound;
  return (
    <PublicScope>
      <main className="vb-pub">
        <header className="vb-pub-head">
          <h1 className="vb-pub-h1">{t.title}</h1>
        </header>
        <div className="vb-pub-card">
          <p>{t.note}</p>
          <Link className="vb-ov-btn" href="/overview">
            {t.back}
          </Link>
        </div>
        <footer className="vb-pub-foot">
          <BrandMark size={28} />
        </footer>
      </main>
    </PublicScope>
  );
}
