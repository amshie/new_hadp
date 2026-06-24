(() => {
  "use strict";

  const qs = (selector, root = document) => root.querySelector(selector);
  const qsa = (selector, root = document) =>
    Array.from(root.querySelectorAll(selector));

  const ICONS = {
    alert:
      '<path d="M12 3 2.8 20h18.4z"></path><path d="M12 9v4M12 17h.01"></path>',
    check: '<path d="m5 12 4 4L19 6"></path>',
    arrow: '<path d="M5 12h14M14 7l5 5-5 5"></path>',
    flask:
      '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"></path><path d="M7.5 15h9"></path>',
    shield:
      '<path d="M12 3 4.5 6v5.5c0 4.8 3.1 7.8 7.5 9.5 4.4-1.7 7.5-4.7 7.5-9.5V6z"></path><path d="m9 12 2 2 4-4"></path>',
    heart:
      '<path d="M20.8 5.6a5.2 5.2 0 0 0-7.4 0L12 7l-1.4-1.4a5.2 5.2 0 0 0-7.4 7.4L12 21l8.8-8a5.2 5.2 0 0 0 0-7.4z"></path>',
    brain:
      '<path d="M9.5 4.5A3.5 3.5 0 0 0 6 8v.2A3.5 3.5 0 0 0 4.5 15 3.5 3.5 0 0 0 8 18.5h1.5zM14.5 4.5A3.5 3.5 0 0 1 18 8v.2A3.5 3.5 0 0 1 19.5 15a3.5 3.5 0 0 1-3.5 3.5h-1.5z"></path><path d="M9.5 9H7M14.5 9H17M9.5 14H7.5M14.5 14h2"></path>',
    bone: '<path d="M17.5 3a2.5 2.5 0 0 0-2.3 3.5l-6.7 6.7A2.5 2.5 0 1 0 5 16.5a2.5 2.5 0 1 0 3.3 3.3l6.7-6.7A2.5 2.5 0 1 0 18.5 9a2.5 2.5 0 1 0-1-6z"></path>',
    leaf: '<path d="M20.8 4.2C14 4 6.2 5 4 12c-1.4 4.4 2.3 7.7 6.4 6.5 5.9-1.8 7.5-8.4 10.4-14.3z"></path><path d="M4.8 19.2C8 15.4 11 12.7 16.7 9.6"></path>',
  };

  function icon(name, className = "") {
    return `<svg class="icon ${className}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ICONS.alert}</svg>`;
  }

  function toast(message, tone = "default") {
    let region = qs(".toast-region");
    if (!region) {
      region = document.createElement("div");
      region.className = "toast-region";
      region.setAttribute("aria-live", "polite");
      region.setAttribute("aria-atomic", "true");
      document.body.appendChild(region);
    }
    const item = document.createElement("div");
    item.className = `toast${tone === "success" ? " success" : ""}`;
    item.innerHTML = `${icon(tone === "success" ? "check" : "alert")}<span>${message}</span>`;
    region.appendChild(item);
    window.setTimeout(() => {
      item.style.opacity = "0";
      item.style.transform = "translateY(8px)";
      item.style.transition = "opacity .18s ease, transform .18s ease";
      window.setTimeout(() => item.remove(), 190);
    }, 3200);
  }

  function initYear() {
    qsa("[data-current-year]").forEach((element) => {
      element.textContent = String(new Date().getFullYear());
    });
  }

  function initUserMenu() {
    const button = qs("[data-user-menu-button]");
    const menu = qs("[data-user-menu]");
    if (!button || !menu) return;

    const setOpen = (open) => {
      menu.classList.toggle("hidden", !open);
      button.setAttribute("aria-expanded", String(open));
    };

    button.addEventListener("click", (event) => {
      event.stopPropagation();
      setOpen(menu.classList.contains("hidden"));
    });
    menu.addEventListener("click", (event) => event.stopPropagation());
    document.addEventListener("click", () => setOpen(false));
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") setOpen(false);
    });
  }

  const DEMO_MESSAGES = {
    reset:
      "Passwort-Wiederherstellung ist im statischen Prototyp nicht angebunden.",
    sso: "Klinik-SSO ist als spätere Integration vorgesehen.",
    backup:
      "Backup-Codes werden in der Produktivversion über den Identity Provider verwaltet.",
    "clinic-switch":
      "Der Klinikwechsel ist im Prototyp nur visuell dargestellt.",
    notifications: "Keine weiteren Benachrichtigungen in diesem Prototyp.",
    import: "Der Import-Workflow folgt im nächsten vertikalen Slice.",
    "new-patient":
      "Die Patienteneinladung ist noch nicht mit einem Backend verbunden.",
    sort: "Die Liste ist im Prototyp bereits nach Priorität sortiert.",
    "review-imports":
      "Die Importprüfung ist als nächster MVP-Screen vorgesehen.",
    "open-source":
      "Quelldokumente würden hier in einem sicheren Viewer geöffnet.",
    more: "Weitere Patientenaktionen sind im Prototyp nicht angebunden.",
    "export-evidence":
      "Der Evidenzexport ist im statischen Prototyp nicht angebunden.",
    defer: "Der Vorgang wurde im Prototyp nicht verändert.",
  };

  function initDemoActions() {
    qsa("[data-demo-action]").forEach((element) => {
      element.addEventListener("click", (event) => {
        event.preventDefault();
        const key = element.getAttribute("data-demo-action");
        toast(
          DEMO_MESSAGES[key] ||
            "Diese Aktion ist im statischen Prototyp nicht angebunden.",
        );
      });
    });

    qsa('a[href="#"]:not([data-demo-action])').forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        toast("Diese Ansicht ist im Prototyp noch nicht umgesetzt.");
      });
    });
  }

  function showAuthState(name) {
    qsa("[data-auth-state]").forEach((state) => {
      state.classList.toggle(
        "is-active",
        state.getAttribute("data-auth-state") === name,
      );
    });
    if (name === "twofactor") {
      window.setTimeout(() => qs("[data-code-inputs] input")?.focus(), 60);
    }
  }

  function initAuth() {
    if (document.body.dataset.page !== "auth") return;

    qsa("[data-auth-target]").forEach((button) => {
      button.addEventListener("click", () =>
        showAuthState(button.getAttribute("data-auth-target")),
      );
    });

    const passwordToggle = qs("[data-password-toggle]");
    const password = qs("#password");
    passwordToggle?.addEventListener("click", () => {
      const visible = password.type === "text";
      password.type = visible ? "password" : "text";
      passwordToggle.textContent = visible ? "Anzeigen" : "Ausblenden";
      passwordToggle.setAttribute("aria-pressed", String(!visible));
    });

    qs("#signin-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!event.currentTarget.reportValidity()) return;
      showAuthState("twofactor");
    });

    const codeInputs = qsa("[data-code-inputs] input");
    codeInputs.forEach((input, index) => {
      input.addEventListener("input", () => {
        input.value = input.value.replace(/\D/g, "").slice(0, 1);
        if (input.value && index < codeInputs.length - 1)
          codeInputs[index + 1].focus();
      });
      input.addEventListener("keydown", (event) => {
        if (event.key === "Backspace" && !input.value && index > 0)
          codeInputs[index - 1].focus();
        if (event.key === "ArrowLeft" && index > 0)
          codeInputs[index - 1].focus();
        if (event.key === "ArrowRight" && index < codeInputs.length - 1)
          codeInputs[index + 1].focus();
      });
      input.addEventListener("paste", (event) => {
        const digits = (event.clipboardData?.getData("text") || "")
          .replace(/\D/g, "")
          .slice(0, 6);
        if (!digits) return;
        event.preventDefault();
        digits.split("").forEach((digit, digitIndex) => {
          if (codeInputs[digitIndex]) codeInputs[digitIndex].value = digit;
        });
        codeInputs[Math.min(digits.length, codeInputs.length) - 1]?.focus();
      });
    });

    qs("#twofactor-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const code = codeInputs.map((input) => input.value).join("");
      if (code.length !== 6) {
        toast("Bitte geben Sie alle sechs Ziffern ein.");
        return;
      }
      window.location.href = "worklist.html";
    });

    qs("#unlock-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!event.currentTarget.reportValidity()) return;
      window.location.href = "worklist.html";
    });
  }

  const WORKLIST_PATIENTS = [
    {
      initials: "JW",
      name: "Jonas Weber",
      id: "P-2026-0023",
      profile: "M · 52 J.",
      assessment: "#1 · Baseline",
      attentionTone: "danger",
      attention: "2 Regelhinweise",
      attentionDetail: "Herz-Kreislauf · Metabolisch",
      quality: 64,
      status: "awaiting",
      updated: "vor 38 Min.",
      open: true,
    },
    {
      initials: "AH",
      name: "Amelia Hart",
      id: "P-2026-0017",
      profile: "F · 45 J.",
      assessment: "#2 · Verlauf",
      attentionTone: "danger",
      attention: "1 Regelhinweis",
      attentionDetail: "Herz-Kreislauf",
      quality: 71,
      status: "awaiting",
      updated: "vor 2 h",
      open: true,
    },
    {
      initials: "LO",
      name: "Liam O'Connor",
      id: "P-2026-0028",
      profile: "M · 44 J.",
      assessment: "#1 · Baseline",
      attentionTone: "success",
      attention: "Keine Eskalation",
      attentionDetail: "Routineprüfung",
      quality: 79,
      status: "awaiting",
      updated: "vor 4 h",
      open: true,
    },
    {
      initials: "MD",
      name: "Mehmet Demir",
      id: "P-2026-0031",
      profile: "M · 47 J.",
      assessment: "#1 · Import",
      attentionTone: "warning",
      attention: "3 Zuordnungen",
      attentionDetail: "Einheiten bestätigen",
      quality: 46,
      status: "import",
      updated: "vor 5 h",
      open: false,
    },
    {
      initials: "CB",
      name: "Clara Bauer",
      id: "P-2026-0009",
      profile: "F · 38 J.",
      assessment: "#3 · Verlauf",
      attentionTone: "success",
      attention: "Review signiert",
      attentionDetail: "Keine offenen Hinweise",
      quality: 88,
      status: "physician",
      updated: "gestern",
      open: false,
    },
    {
      initials: "DN",
      name: "David Novak",
      id: "P-2026-0034",
      profile: "M · 50 J.",
      assessment: "#1 · Datensammlung",
      attentionTone: "warning",
      attention: "Panel unvollständig",
      attentionDetail: "3 von 8 Quellen fehlen",
      quality: 42,
      status: "collecting",
      updated: "vor 2 T",
      open: false,
    },
    {
      initials: "SR",
      name: "Sofia Rossi",
      id: "P-2026-0015",
      profile: "F · 61 J.",
      assessment: "#2 · Verlauf",
      attentionTone: "warning",
      attention: "1 Beobachtung",
      attentionDetail: "Entzündung beobachten",
      quality: 82,
      status: "finalized",
      updated: "vor 3 T",
      open: false,
    },
    {
      initials: "AS",
      name: "Anna Schmidt",
      id: "P-2026-0006",
      profile: "F · 55 J.",
      assessment: "#4 · Verlauf",
      attentionTone: "success",
      attention: "Ohne Hinweis",
      attentionDetail: "Alle Bereiche geprüft",
      quality: 90,
      status: "finalized",
      updated: "vor 4 T",
      open: false,
    },
  ];

  const WORKLIST_STATUS = {
    awaiting: {
      badge: "badge-brand",
      label: "Klinischer Review",
      action: "Prüfen",
    },
    import: {
      badge: "badge-warning",
      label: "Importprüfung",
      action: "Öffnen",
    },
    physician: {
      badge: "badge-info",
      label: "Ärztliche Prüfung",
      action: "Ansehen",
    },
    collecting: {
      badge: "badge-neutral",
      label: "Datensammlung",
      action: "Ansehen",
    },
    finalized: {
      badge: "badge-success",
      label: "Finalisiert",
      action: "Bericht",
    },
  };

  function worklistRow(patient) {
    const status = WORKLIST_STATUS[patient.status];
    const qualityClass =
      patient.quality < 60 ? "danger" : patient.quality < 70 ? "warning" : "";
    const attentionIcon =
      patient.attentionTone === "success" ? icon("check") : icon("alert");
    return `
      <tr tabindex="0" data-patient-id="${patient.id}" data-open="${patient.open}">
        <td data-label="Patient"><div class="patient-cell"><div class="patient-avatar">${patient.initials}</div><div><div class="patient-name">${patient.name}</div><div class="patient-meta">${patient.id} · ${patient.profile}</div></div></div></td>
        <td data-label="Assessment"><div class="assessment-cell"><strong>Assessment ${patient.assessment}</strong></div></td>
        <td data-label="Aufmerksamkeit"><div class="attention ${patient.attentionTone}">${attentionIcon}<div><strong>${patient.attention}</strong><span>${patient.attentionDetail}</span></div></div></td>
        <td data-label="Datenqualität"><div class="quality-cell"><div class="progress ${qualityClass}"><span style="width:${patient.quality}%"></span></div><span class="quality-value num">${patient.quality}%</span></div></td>
        <td data-label="Status"><span class="badge ${status.badge}">${status.label}</span></td>
        <td data-label="Aktualisiert"><span class="num" style="font-size:10.5px;color:var(--muted)">${patient.updated}</span></td>
        <td data-label="Aktion"><a class="row-action" href="${patient.open ? "patient-review.html" : "#"}" data-row-action>${status.action} →</a></td>
      </tr>`;
  }

  function initWorklist() {
    if (document.body.dataset.page !== "worklist") return;
    const body = qs("#worklist-rows");
    const empty = qs("#worklist-empty");
    const search = qs("[data-worklist-search]");
    let filter = "awaiting";
    let term = "";

    const render = () => {
      const rows = WORKLIST_PATIENTS.filter((patient) => {
        const matchesFilter = filter === "all" || patient.status === filter;
        const haystack =
          `${patient.name} ${patient.id} ${patient.attentionDetail}`.toLowerCase();
        return matchesFilter && haystack.includes(term.toLowerCase());
      });
      body.innerHTML = rows.map(worklistRow).join("");
      empty.classList.toggle("hidden", rows.length > 0);
    };

    qsa("[data-worklist-filter]").forEach((tab) => {
      tab.addEventListener("click", () => {
        filter = tab.getAttribute("data-worklist-filter");
        qsa("[data-worklist-filter]").forEach((item) =>
          item.setAttribute("aria-selected", String(item === tab)),
        );
        render();
      });
    });

    search?.addEventListener("input", () => {
      term = search.value.trim();
      render();
    });

    body.addEventListener("click", (event) => {
      const action = event.target.closest("[data-row-action]");
      const row = event.target.closest("tr");
      if (!row) return;
      const canOpen = row.dataset.open === "true";
      if (action && !canOpen) {
        event.preventDefault();
        toast(
          "Diese Detailansicht ist im Prototyp nur für offene Reviews umgesetzt.",
        );
        return;
      }
      if (!action && canOpen) window.location.href = "patient-review.html";
      if (!action && !canOpen)
        toast("Diese Detailansicht ist im Prototyp nicht umgesetzt.");
    });

    body.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const row = event.target.closest("tr");
      if (!row) return;
      event.preventDefault();
      if (row.dataset.open === "true")
        window.location.href = "patient-review.html";
      else toast("Diese Detailansicht ist im Prototyp nicht umgesetzt.");
    });

    render();
  }

  const REVIEW_DOMAINS = [
    {
      id: "metabolic",
      name: "Metabolisch",
      icon: "flask",
      count: 8,
      trend: {
        tone: "success",
        label: "Verbessert",
        detail: "62 → 78 %",
        symbol: "↑",
      },
      rules: { tone: "medium", label: "Moderat", detail: "2 Hinweise" },
      function: {
        tone: "success",
        label: "Verbessert",
        detail: "65 → 76 %",
        symbol: "↑",
      },
      quality: 82,
      badges: [
        ["success", "Messwerte verbessert"],
        ["warning", "2 Hinweise"],
        ["info", "Datenqualität 82 %"],
      ],
      summary:
        "Die verfügbaren Stoffwechselmarker zeigen insgesamt eine günstige Entwicklung, insbesondere bei Glukoseregulation und Triglyceriden. Zwei Regelhinweise bleiben für die klinische Einordnung offen.",
      sources: ["Labor · 18.06.2026", "Klinikmessung · 12.06.2026"],
      qualityHistory: [60, 68, 74, 79, 82],
      markers: [
        [
          "HbA1c",
          "5,4 %",
          "5,8 %",
          "↓ 0,4 %",
          "4,0–5,6 %",
          "Labor 18.06.",
          "good",
        ],
        [
          "Nüchternglukose",
          "91 mg/dL",
          "106 mg/dL",
          "↓ 15",
          "70–99 mg/dL",
          "Labor 18.06.",
          "good",
        ],
        [
          "Nüchterninsulin",
          "7,8 µIU/mL",
          "12,0 µIU/mL",
          "↓ 4,2",
          "2,6–24,9",
          "Labor 18.06.",
          "good",
        ],
        ["HOMA-IR", "1,8", "2,9", "↓ 1,1", "berechnet", "Regel v1.2", "good"],
        [
          "Triglyceride",
          "102 mg/dL",
          "127 mg/dL",
          "↓ 25",
          "<150 mg/dL",
          "Labor 18.06.",
          "good",
        ],
        [
          "HDL-C",
          "61 mg/dL",
          "53 mg/dL",
          "↑ 8",
          ">50 mg/dL",
          "Labor 18.06.",
          "good",
        ],
        [
          "LDL-C",
          "118 mg/dL",
          "136 mg/dL",
          "↓ 18",
          "<116 mg/dL",
          "Labor 18.06.",
          "good",
        ],
        [
          "hs-CRP",
          "1,7 mg/L",
          "2,9 mg/L",
          "↓ 1,2",
          "<3,0 mg/L",
          "Labor 18.06.",
          "good",
        ],
      ],
    },
    {
      id: "immune",
      name: "Immun / Entzündung",
      icon: "shield",
      count: 6,
      trend: {
        tone: "info",
        label: "Stabil",
        detail: "keine klare Änderung",
        symbol: "→",
      },
      rules: { tone: "high", label: "Hoch", detail: "3 Hinweise" },
      function: {
        tone: "info",
        label: "Stabil",
        detail: "keine klare Änderung",
        symbol: "→",
      },
      quality: 68,
      badges: [
        ["info", "Verlauf stabil"],
        ["danger", "3 Hinweise"],
        ["warning", "Datenqualität 68 %"],
      ],
      summary:
        "Mehrere Entzündungsmarker liegen höher als in der Baseline. Die Datenabdeckung ist jedoch nur moderat. Akute Infekte, Medikamente und Bedingungen der Probenentnahme sollten vor einer Einordnung geprüft werden.",
      sources: ["Labor · 18.06.2026"],
      qualityHistory: [70, 66, 69, 70, 68],
      markers: [
        [
          "hs-CRP",
          "3,3 mg/L",
          "2,9 mg/L",
          "↑ 0,4",
          "<3,0 mg/L",
          "Labor 18.06.",
          "bad",
        ],
        [
          "IL-6",
          "4,2 pg/mL",
          "3,4 pg/mL",
          "↑ 0,8",
          "<3,4 pg/mL",
          "Labor 18.06.",
          "bad",
        ],
        [
          "TNF-α",
          "8,1 pg/mL",
          "7,8 pg/mL",
          "↑ 0,3",
          "0,0–8,1",
          "Labor 18.06.",
          "bad",
        ],
        [
          "Ferritin",
          "86 ng/mL",
          "96 ng/mL",
          "↓ 10",
          "15–150",
          "Labor 18.06.",
          "flat",
        ],
        [
          "Leukozyten",
          "6,1 ×10⁹/L",
          "5,6 ×10⁹/L",
          "↑ 0,5",
          "4,0–10,0",
          "Labor 18.06.",
          "flat",
        ],
        ["NLR", "2,5", "2,3", "↑ 0,2", "berechnet", "Regel v1.2", "bad"],
      ],
    },
    {
      id: "cardio",
      name: "Herz-Kreislauf",
      icon: "heart",
      count: 7,
      trend: {
        tone: "success",
        label: "Verbessert",
        detail: "55 → 70 %",
        symbol: "↑",
      },
      rules: { tone: "high", label: "Hoch", detail: "4 Hinweise" },
      function: {
        tone: "info",
        label: "Stabil",
        detail: "keine klare Änderung",
        symbol: "→",
      },
      quality: 71,
      badges: [
        ["success", "Verlauf verbessert"],
        ["danger", "4 Regelhinweise"],
        ["info", "Datenqualität 71 %"],
      ],
      summary:
        "ApoB, Blutdruck und Ruhepuls haben sich gegenüber der Baseline verbessert. Der aktuelle Regelstatus bleibt wegen persistierend hohem Lp(a) und einem Anstieg des Koronarkalk-Scores auffällig. Bildgebungsbericht und ärztliche Eskalation prüfen.",
      sources: [
        "Labor · 18.06.2026",
        "Withings · 7-Tage-Mittel",
        "Oura · 14-Tage-Mittel",
        "CT-Bericht · 04.06.2026",
      ],
      qualityHistory: [56, 62, 67, 69, 71],
      markers: [
        [
          "ApoB",
          "94 mg/dL",
          "106 mg/dL",
          "↓ 12",
          "<90 mg/dL",
          "Labor 18.06.",
          "good",
        ],
        [
          "LDL-C",
          "118 mg/dL",
          "136 mg/dL",
          "↓ 18",
          "<116 mg/dL",
          "Labor 18.06.",
          "good",
        ],
        [
          "Lp(a)",
          "162 nmol/L",
          "160 nmol/L",
          "→ +2",
          "<75 nmol/L",
          "Labor 18.06.",
          "flat",
        ],
        [
          "Systolischer Blutdruck",
          "124 mmHg",
          "130 mmHg",
          "↓ 6",
          "<130 mmHg",
          "Withings 7 T.",
          "good",
        ],
        [
          "Diastolischer Blutdruck",
          "78 mmHg",
          "82 mmHg",
          "↓ 4",
          "<80 mmHg",
          "Withings 7 T.",
          "good",
        ],
        [
          "Ruhepuls",
          "61 bpm",
          "66 bpm",
          "↓ 5",
          "individuelle Baseline",
          "Oura 14 T.",
          "good",
        ],
        [
          "Koronarkalk",
          "146 Agatston",
          "134 Agatston",
          "↑ 12",
          "Bildgebung",
          "CT 04.06.",
          "bad",
        ],
      ],
    },
    {
      id: "neuro",
      name: "Neurokognitiv",
      icon: "brain",
      count: 5,
      trend: {
        tone: "info",
        label: "Stabil",
        detail: "keine klare Änderung",
        symbol: "→",
      },
      rules: { tone: "medium", label: "Moderat", detail: "2 Hinweise" },
      function: {
        tone: "success",
        label: "Verbessert",
        detail: "60 → 72 %",
        symbol: "↑",
      },
      quality: 72,
      badges: [
        ["success", "Funktion verbessert"],
        ["warning", "2 Hinweise"],
        ["info", "Datenqualität 72 %"],
      ],
      summary:
        "Funktionelle kognitive Messungen und unterstützende Beobachtungen zeigen eine günstige Richtung. Zwei moderate Regelhinweise bleiben offen; Testbedingungen und Schlafqualität sollten bestätigt werden.",
      sources: [
        "Kognitionstest · 16.06.2026",
        "Labor · 18.06.2026",
        "Oura · 30-Tage-Mittel",
      ],
      qualityHistory: [62, 65, 68, 70, 72],
      markers: [
        [
          "Verarbeitungsgeschwindigkeit",
          "72. Perzentil",
          "66. Perzentil",
          "↑ 6",
          "altersadjustiert",
          "Kognition 16.06.",
          "good",
        ],
        [
          "Arbeitsgedächtnis",
          "68. Perzentil",
          "64. Perzentil",
          "↑ 4",
          "altersadjustiert",
          "Kognition 16.06.",
          "good",
        ],
        [
          "Homocystein",
          "9,8 µmol/L",
          "11,8 µmol/L",
          "↓ 2,0",
          "5,0–15,0",
          "Labor 18.06.",
          "good",
        ],
        [
          "Omega-3-Index",
          "7,4 %",
          "6,2 %",
          "↑ 1,2",
          "Ziel 8–12 %",
          "Labor 18.06.",
          "good",
        ],
        [
          "Schlafeffizienz",
          "86 %",
          "81 %",
          "↑ 5",
          "individuelle Baseline",
          "Oura 30 T.",
          "good",
        ],
      ],
    },
    {
      id: "msk",
      name: "Muskel-Skelett",
      icon: "bone",
      count: 4,
      trend: {
        tone: "success",
        label: "Verbessert",
        detail: "50 → 68 %",
        symbol: "↑",
      },
      rules: { tone: "none", label: "Niedrig", detail: "keine Hinweise" },
      function: {
        tone: "success",
        label: "Verbessert",
        detail: "58 → 71 %",
        symbol: "↑",
      },
      quality: 85,
      badges: [
        ["success", "Messwerte verbessert"],
        ["success", "Keine Hinweise"],
        ["info", "Datenqualität 85 %"],
      ],
      summary:
        "Kraft, fettfreie Masse und Ganggeschwindigkeit haben sich gegenüber der Baseline verbessert. In den verfügbaren Beobachtungen bestehen derzeit keine Regelhinweise.",
      sources: ["Klinikmessung · 12.06.2026", "DXA · 10.06.2026"],
      qualityHistory: [70, 75, 80, 83, 85],
      markers: [
        [
          "Griffkraft",
          "31 kg",
          "27 kg",
          "↑ 4",
          "alters-/geschlechtsbezogen",
          "Klinik 12.06.",
          "good",
        ],
        [
          "Appendikuläre Magermasse",
          "18,4 kg",
          "17,2 kg",
          "↑ 1,2",
          "DXA-Bericht",
          "DXA 10.06.",
          "good",
        ],
        [
          "Knochendichte T-Score",
          "−0,4",
          "−0,6",
          "↑ 0,2",
          ">−1,0",
          "DXA 10.06.",
          "good",
        ],
        [
          "Ganggeschwindigkeit",
          "1,32 m/s",
          "1,22 m/s",
          "↑ 0,10",
          ">1,0 m/s",
          "Klinik 12.06.",
          "good",
        ],
      ],
    },
    {
      id: "regen",
      name: "Regenerative Kapazität",
      icon: "leaf",
      count: 3,
      trend: {
        tone: "info",
        label: "Stabil",
        detail: "keine klare Änderung",
        symbol: "→",
      },
      rules: { tone: "medium", label: "Moderat", detail: "1 Hinweis" },
      function: {
        tone: "info",
        label: "Stabil",
        detail: "keine klare Änderung",
        symbol: "→",
      },
      quality: 65,
      badges: [
        ["info", "Verlauf stabil"],
        ["warning", "1 Hinweis"],
        ["warning", "Datenqualität 65 %"],
      ],
      summary:
        "Die explorativen altersbezogenen Beobachtungen bleiben weitgehend stabil. Die Quellenabdeckung ist begrenzt; der Bereich sollte nicht isoliert für klinische Entscheidungen verwendet werden.",
      sources: ["Speziallabor · 02.06.2026"],
      qualityHistory: [66, 64, 67, 66, 65],
      markers: [
        [
          "Telomerlänge",
          "6,7 kb",
          "6,8 kb",
          "→ −0,1",
          "assayspezifisch",
          "Speziallabor 02.06.",
          "flat",
        ],
        [
          "Methylierungsalter",
          "44,8 J.",
          "44,6 J.",
          "→ +0,2",
          "modellspezifisch",
          "Speziallabor 02.06.",
          "flat",
        ],
        [
          "NAD+",
          "31 µM",
          "29 µM",
          "↑ 2",
          "assayspezifisch",
          "Speziallabor 02.06.",
          "good",
        ],
      ],
    },
  ];

  function trendMarkup(trend) {
    return `<div class="trend ${trend.tone}"><span class="trend-symbol">${trend.symbol}</span><span><strong>${trend.label}</strong><small>${trend.detail}</small></span></div>`;
  }

  function rulesMarkup(rules) {
    return `<div class="rule-match ${rules.tone}"><span class="rule-bars"><span></span><span></span><span></span></span><span><strong>${rules.label}</strong><small>${rules.detail}</small></span></div>`;
  }

  function domainRow(domain, selected) {
    return `<tr tabindex="0" data-domain-id="${domain.id}" aria-selected="${selected}">
      <td data-label="Bereich"><div class="domain-name"><span class="domain-icon">${icon(domain.icon)}</span><span><strong>${domain.name}</strong><span>${domain.count} Marker</span></span></div></td>
      <td data-label="Messwertverlauf">${trendMarkup(domain.trend)}</td>
      <td data-label="Regelhinweise">${rulesMarkup(domain.rules)}</td>
      <td data-label="Funktion">${trendMarkup(domain.function)}</td>
      <td data-label="Datenqualität"><div class="quality-cell"><div class="progress ${domain.quality < 70 ? "warning" : ""}"><span style="width:${domain.quality}%"></span></div><span class="quality-value num">${domain.quality}%</span></div></td>
    </tr>`;
  }

  function sparkline(values) {
    const width = 300;
    const height = 52;
    const pad = 4;
    const min = Math.min(...values) - 4;
    const max = Math.max(...values) + 4;
    const x = (index) =>
      pad + (index * (width - pad * 2)) / (values.length - 1);
    const y = (value) =>
      height - pad - ((value - min) / (max - min)) * (height - pad * 2);
    const path = values
      .map(
        (value, index) =>
          `${index ? "L" : "M"}${x(index).toFixed(1)} ${y(value).toFixed(1)}`,
      )
      .join(" ");
    const area = `${path} L${width - pad} ${height - pad} L${pad} ${height - pad} Z`;
    const endX = x(values.length - 1).toFixed(1);
    const endY = y(values[values.length - 1]).toFixed(1);
    return `<defs><linearGradient id="quality-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#0c6b5d" stop-opacity=".22"></stop><stop offset="100%" stop-color="#0c6b5d" stop-opacity="0"></stop></linearGradient></defs><line x1="4" y1="47" x2="296" y2="47" stroke="#dce4e6" stroke-width="1"></line><path d="${area}" fill="url(#quality-area)"></path><path d="${path}" fill="none" stroke="#0c6b5d" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path><circle cx="${endX}" cy="${endY}" r="3.3" fill="#117c6d" stroke="#fff" stroke-width="1.5"></circle>`;
  }

  function markerRow(marker) {
    const changeClass =
      marker[6] === "good"
        ? "change-up"
        : marker[6] === "bad"
          ? "change-down"
          : "change-flat";
    return `<tr><td><span class="marker-name">${marker[0]}</span></td><td class="num">${marker[1]}</td><td class="num">${marker[2]}</td><td><span class="${changeClass}">${marker[3]}</span></td><td>${marker[4]}</td><td class="source">${marker[5]}</td></tr>`;
  }

  function initReview() {
    if (document.body.dataset.page !== "review") return;
    let selectedId = "cardio";
    const domainRows = qs("#domain-rows");

    const renderEvidence = () => {
      const domain = REVIEW_DOMAINS.find((item) => item.id === selectedId);
      qs("#evidence-title").textContent = domain.name;
      qs("#evidence-badges").innerHTML = domain.badges
        .map(
          ([tone, label]) =>
            `<span class="badge badge-${tone} no-dot">${label}</span>`,
        )
        .join("");
      qs("#evidence-summary-text").textContent = domain.summary;
      qs("#evidence-source-links").innerHTML = domain.sources
        .map(
          (source) =>
            `<a class="source-link" href="#" data-source-link>${source}</a>`,
        )
        .join("");
      qs("#quality-current").textContent = `${domain.quality}%`;
      qs("#quality-spark").innerHTML = sparkline(domain.qualityHistory);
      qs("#marker-count-copy").textContent =
        `${domain.count} Marker · gemessene Werte, Einheiten, Referenzintervalle und Quellen`;
      qs("#marker-rows").innerHTML = domain.markers.map(markerRow).join("");
      qsa("[data-source-link]").forEach((link) =>
        link.addEventListener("click", (event) => {
          event.preventDefault();
          toast(
            "Das ausgewählte Quelldokument würde in einem sicheren Viewer geöffnet.",
          );
        }),
      );
    };

    const renderDomains = () => {
      domainRows.innerHTML = REVIEW_DOMAINS.map((domain) =>
        domainRow(domain, domain.id === selectedId),
      ).join("");
    };

    const selectDomain = (id) => {
      selectedId = id;
      renderDomains();
      renderEvidence();
    };

    domainRows.addEventListener("click", (event) => {
      const row = event.target.closest("[data-domain-id]");
      if (row) selectDomain(row.dataset.domainId);
    });
    domainRows.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const row = event.target.closest("[data-domain-id]");
      if (!row) return;
      event.preventDefault();
      selectDomain(row.dataset.domainId);
    });

    const dialog = qs("[data-review-dialog]");
    const openButton = qs("[data-open-review-dialog]");
    const closeButtons = qsa("[data-close-review-dialog]");
    const confirmation = qs("[data-review-confirm]");
    const confirmButton = qs("[data-confirm-review]");
    let previousFocus = null;

    const setDialogOpen = (open) => {
      dialog.classList.toggle("hidden", !open);
      document.body.classList.toggle("modal-open", open);
      if (open) {
        previousFocus = document.activeElement;
        confirmation.checked = false;
        confirmButton.disabled = true;
        window.setTimeout(() => confirmation.focus(), 30);
      } else {
        previousFocus?.focus?.();
      }
    };

    openButton.addEventListener("click", () => setDialogOpen(true));
    closeButtons.forEach((button) =>
      button.addEventListener("click", () => setDialogOpen(false)),
    );
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) setDialogOpen(false);
    });
    confirmation.addEventListener("change", () => {
      confirmButton.disabled = !confirmation.checked;
    });
    confirmButton.addEventListener("click", () => {
      setDialogOpen(false);
      const headerBadge = qs(".patient-heading .badge");
      headerBadge.className = "badge badge-info";
      headerBadge.textContent = "An ärztliche Prüfung weitergeleitet";
      openButton.disabled = true;
      openButton.innerHTML = `${icon("check")} Review signiert`;
      const activeStep = qs(".audit-step.active");
      if (activeStep) {
        activeStep.classList.remove("active");
        activeStep.classList.add("done");
        activeStep.querySelector(".audit-step-dot").textContent = "✓";
        activeStep.querySelector(".audit-step-copy span").textContent =
          "Signiert";
        const nextStep = activeStep.nextElementSibling?.nextElementSibling;
        nextStep?.classList.add("active");
        nextStep?.querySelector(".audit-step-copy span") &&
          (nextStep.querySelector(".audit-step-copy span").textContent =
            "In Prüfung");
      }
      toast(
        "Klinischer Review signiert und zur ärztlichen Prüfung weitergeleitet.",
        "success",
      );
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !dialog.classList.contains("hidden"))
        setDialogOpen(false);
    });

    renderDomains();
    renderEvidence();
  }

  document.addEventListener("DOMContentLoaded", () => {
    initYear();
    initUserMenu();
    initDemoActions();
    initAuth();
    initWorklist();
    initReview();
  });
})();
