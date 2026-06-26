import { redirect } from "next/navigation";

import { me } from "@/lib/api";

export default async function Home() {
  // Authed users land on the VitaBahn dashboard (/overview), which replaces the old
  // /worklist as the home (ADR-0005). The login gate is unchanged.
  let target = "/login";
  try {
    await me();
    target = "/overview";
  } catch {
    target = "/login";
  }
  redirect(target);
}
