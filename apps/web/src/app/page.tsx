import { redirect } from "next/navigation";

import { me } from "@/lib/api";

export default async function Home() {
  let target = "/login";
  try {
    await me();
    target = "/worklist";
  } catch {
    target = "/login";
  }
  redirect(target);
}
