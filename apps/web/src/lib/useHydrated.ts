"use client";

import { useEffect, useState } from "react";

// False in the server's markup and until React has taken the page over.
//
// A form whose submit is handled in script must not be usable before that: the browser would
// submit it natively — a GET to the same address, which reloads the page, drops what was
// entered and writes it into the URL (an e-mail address, a file's name), where the address
// bar, the history and the server's access log keep it. Such a form keeps its submit button
// disabled until this is true; a disabled default button also stops submission by the Enter
// key.
export function useHydrated(): boolean {
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  return hydrated;
}
