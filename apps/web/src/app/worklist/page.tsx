import { redirect } from "next/navigation";

// /worklist is retired (ADR-0005): the VitaBahn /overview replaces it as the home.
// Kept as a redirect so existing links/bookmarks don't 404.
export default function WorklistPage() {
  redirect("/overview");
}
