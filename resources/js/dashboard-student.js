let userRoutes = [];
let currentCompanies = [];

const svgIcon = (id, extraClass = "icon") =>
    `<span class="${extraClass}"><svg><use href="#${id}"></use></svg></span>`;

const modeLabel = {
    "driving-car": "Auto",
    "foot-walking": "A piedi",
    "cycling-regular": "Bici",
};
const modeIcon = {
    "driving-car": svgIcon("i-car"),
    "foot-walking": svgIcon("i-walk"),
    "cycling-regular": svgIcon("i-bike"),
};
const modeBadge = {
    "driving-car": "car",
    "foot-walking": "walk",
    "cycling-regular": "bike",
};

const SECTIONS = [
    "sectionDashboard",
    "sectionAziende",
    "sectionPercorsi",
    "sectionProfilo",
    "sectionImpostazioni",
];
let aziendeLoaded = false;
let percorsiLoaded = false;
let currentFilter = "all";

function showSection(name) {
    const map = {
        dashboard: "sectionDashboard",
        aziende: "sectionAziende",
        percorsi: "sectionPercorsi",
        profilo: "sectionProfilo",
        impostazioni: "sectionImpostazioni",
    };
    SECTIONS.forEach((id) => {
        document.getElementById(id).classList.add("hidden");
    });
    document.getElementById(map[name]).classList.remove("hidden");

    // Lazy-load al primo accesso
    if (name === "aziende" && !aziendeLoaded) {
        aziendeLoaded = true;
        loadCompanies();
    }
    if (name === "percorsi" && !percorsiLoaded) {
        loadRoutes();
    }

    if (window.innerWidth <= 1100) closeSidebar();
}

function setActive(el) {
    document
        .querySelectorAll(".nav-item")
        .forEach((i) => i.classList.remove("active"));
    if (el) el.classList.add("active");
}

const APPLICATION_STATUS_LABEL = {
    inviata: "Candidatura inviata",
    vista: "Candidatura visualizzata",
    accettata: "Candidatura accettata",
    rifiutata: "Candidatura rifiutata",
};

function offerInitials(name) {
    return String(name || "?")
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((word) => word[0])
        .join("")
        .toUpperCase();
}

function mapOfferToCard(offer) {
    const tags = [
        ...offer.required_skills.map((s) => s.name),
        ...offer.required_soft_skills.map((s) => s.label),
    ];

    return {
        id: offer.id,
        initials: offerInitials(offer.company_name),
        name: offer.company_name,
        sector: offer.title,
        companySector: offer.company_settore || "Settore non specificato",
        matchPct: offer.final_score != null ? Math.round(offer.final_score) : null,
        aiStatus: offer.ai_status,
        explanation: offer.explanation,
        tags,
        description: offer.description || offer.company_descrizione || "Nessuna descrizione disponibile.",
        distanceKm: offer.distance_km != null ? offer.distance_km.toFixed(1) : null,
        durationMin: offer.duration_min != null ? Math.round(offer.duration_min) : null,
        address: offer.company_address || "Indirizzo non disponibile",
        contacts: {
            email: offer.company_email,
            web: offer.company_sito_web,
            phone: offer.company_telefono,
        },
        applicationStatus: offer.application_status,
    };
}

function renderCompanies(offers) {
    currentCompanies = Array.isArray(offers) ? offers.map(mapOfferToCard) : [];
    renderCompanyCards();
}

function getApplyLabel(company) {
    return company.applicationStatus
        ? APPLICATION_STATUS_LABEL[company.applicationStatus] || "Candidato"
        : "Candidati";
}

function renderCompanyCards() {
    const list = document.getElementById("aziendeList");
    const empty = document.getElementById("aziendeEmpty");
    const badge = document.getElementById("badgeAziende");
    const statAziende = document.getElementById("statAziendeMatch");
    const subtitle = document.getElementById("aziendeSubtitle");

    badge.textContent = currentCompanies.length;
    if (statAziende) statAziende.textContent = currentCompanies.length;

    if (currentCompanies.length === 0) {
        list.style.display = "none";
        empty.style.display = "flex";
        subtitle.textContent = "Nessun annuncio compatibile trovato";
        return;
    }

    const n = currentCompanies.length;
    subtitle.textContent = `${n} annunci${n === 1 ? "o" : ""} compatibil${n === 1 ? "e" : "i"} con il tuo profilo`;
    empty.style.display = "none";
    list.style.display = "grid";
    list.innerHTML = "";

    currentCompanies.forEach((c, i) => {
        const isBest = i === 0 && c.matchPct != null;
        const tags = c.tags
            .map((t) => `<span class="co-tag">${escapeHtml(t)}</span>`)
            .join("");
        const card = document.createElement("div");
        card.className = `co-card${isBest ? " best" : ""}`;
        card.dataset.id = c.id;

        const matchBlock =
            c.matchPct != null
                ? `<div class="co-match">
                    <div class="co-pct">${c.matchPct}%</div>
                    <div class="co-pct-label">match</div>
                  </div>`
                : `<div class="co-match">
                    <div class="co-pct-label">In elaborazione…</div>
                  </div>`;

        const applyLabel = getApplyLabel(c);

        card.innerHTML = `
          <div class="co-top">
            <div class="co-row1">
              <div class="co-logo">${c.initials}</div>
              <div class="co-info">
                <div class="co-name">${escapeHtml(c.name)}</div>
                <div class="co-sector">${escapeHtml(c.sector)}</div>
              </div>
              ${matchBlock}
            </div>
            ${c.matchPct != null ? `<div class="co-bar-wrap"><div class="co-bar" style="width:${c.matchPct}%"></div></div>` : ""}
            <div class="co-tags">${tags}</div>
            <div class="co-meta">
              <div class="co-meta-item">${svgIcon("i-pin")}<span>${c.distanceKm != null ? c.distanceKm + " km" : "distanza n/d"}</span></div>
              <div class="co-meta-sep">·</div>
              <div class="co-meta-item">${svgIcon("i-route")}<span>${c.durationMin != null ? c.durationMin + " min in auto" : "durata n/d"}</span></div>
            </div>
          </div>
          <div class="co-card-actions">
            <button class="co-toggle" type="button" data-action="open-company-details" data-company-id="${c.id}">
              Dettagli e contatti
            </button>
            <button class="co-toggle" type="button" data-action="apply-offer" data-company-id="${c.id}" ${c.applicationStatus ? "disabled" : ""}>
              ${applyLabel}
            </button>
          </div>
        `;
        list.appendChild(card);
    });
}

async function loadCompanies() {
    document.getElementById("aziendeLoading").style.display = "flex";
    document.getElementById("aziendeList").style.display = "none";

    try {
        const res = await fetch("/api/students/offers");
        if (!res.ok) throw new Error(`http ${res.status}`);
        renderCompanies(await res.json());
    } catch (err) {
        console.error("Errore caricamento annunci:", err);
        renderCompanies([]);
    } finally {
        document.getElementById("aziendeLoading").style.display = "none";
    }
}

async function applyToOffer(companyId) {
    try {
        const res = await fetch(`/api/students/offers/${companyId}/apply`, { method: "POST" });
        const data = await res.json().catch(() => ({}));

        if (!res.ok) {
            showToast(data.error || "Errore durante l'invio della candidatura");
            return;
        }

        const offer = currentCompanies.find((c) => String(c.id) === String(companyId));
        if (offer) offer.applicationStatus = "inviata";

        showToast("Candidatura inviata");
        renderCompanyCards();
    } catch (err) {
        console.error("Errore candidatura:", err);
        showToast("Errore durante l'invio della candidatura");
    }
}

function getCompanyById(companyId) {
    return currentCompanies.find((company) => String(company.id) === String(companyId));
}

function renderCompanyDetailsModal(company) {
    const content = document.getElementById("companyDetailsContent");
    const explanationBlock =
        company.aiStatus === "ok" && company.explanation
            ? `<div class="co-desc">${escapeHtml(company.explanation)}</div>`
            : `<div class="co-desc">Punteggio calcolato automaticamente in base a skill, soft skill e distanza.</div>`;

    content.innerHTML = `
      <div class="company-modal-hero">
        <div class="company-modal-logo">${company.initials}</div>
        <div class="company-modal-head">
          <div class="company-modal-name">${escapeHtml(company.name)}</div>
          <div class="company-modal-sector">${escapeHtml(company.sector)} · ${escapeHtml(company.companySector)}</div>
        </div>
        <div class="company-modal-match">
          <div class="company-modal-match-pct">${company.matchPct != null ? company.matchPct + "%" : "--"}</div>
          <div class="company-modal-match-label">match</div>
        </div>
      </div>
      <div class="company-modal-tags">
        ${company.tags.map((tag) => `<span class="co-tag">${escapeHtml(tag)}</span>`).join("")}
      </div>
      <div class="company-modal-grid">
        <div class="company-modal-panel">
          <div class="company-modal-section-title">Descrizione</div>
          <div class="co-desc">${escapeHtml(company.description)}</div>
        </div>
        <div class="company-modal-panel">
          <div class="company-modal-section-title">Perché questo match</div>
          ${explanationBlock}
        </div>
        <div class="company-modal-panel">
          <div class="company-modal-section-title">Dettagli</div>
          <div class="company-modal-info-list">
            <div class="co-contact-row">${svgIcon("i-pin")}<span>${escapeHtml(company.address)}</span></div>
            <div class="co-contact-row">${svgIcon("i-route")}<span>${company.distanceKm != null ? company.distanceKm + " km · " + company.durationMin + " min in auto" : "Distanza non disponibile"}</span></div>
          </div>
        </div>
        <div class="company-modal-panel">
          <div class="company-modal-section-title">Contatti</div>
          <div class="co-contacts">
            ${company.contacts.email ? `<div class="co-contact-row">${svgIcon("i-mail")}<a href="mailto:${company.contacts.email}">${escapeHtml(company.contacts.email)}</a></div>` : ""}
            ${company.contacts.web ? `<div class="co-contact-row">${svgIcon("i-link")}<a href="https://${company.contacts.web}" target="_blank" rel="noopener noreferrer">${escapeHtml(company.contacts.web)}</a></div>` : ""}
            ${company.contacts.phone ? `<div class="co-contact-row">${svgIcon("i-phone")}<span>${escapeHtml(company.contacts.phone)}</span></div>` : ""}
          </div>
        </div>
      </div>
      <div class="company-modal-actions">
        <button class="co-map-btn" type="button" data-action="apply-offer" data-company-id="${company.id}" ${company.applicationStatus ? "disabled" : ""}>
          ${svgIcon("i-check")}
          ${getApplyLabel(company)}
        </button>
        <button class="co-map-btn co-map-btn-outline" type="button" data-action="go-to-company-map" data-company-id="${company.id}">
          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
          Mostra percorso sulla mappa
        </button>
      </div>
    `;
}

function openCompanyDetails(companyId) {
    const company = getCompanyById(companyId);
    const overlay = document.getElementById("companyDetailsOverlay");

    if (!company || !overlay) return;

    renderCompanyDetailsModal(company);
    overlay.classList.add("active");
}

function closeCompanyDetails() {
    const overlay = document.getElementById("companyDetailsOverlay");
    if (!overlay) return;
    overlay.classList.remove("active");
}

function renderRoutes(routes, filter = "all") {
    const list = document.getElementById("percorsiList");
    const count = document.getElementById("percorsiCount");

    const filtered =
        filter === "all" ? routes : routes.filter((r) => r.mode === filter);
    count.textContent = routes.length;
    document.getElementById("badgePercorsi").textContent = routes.length;

    if (filtered.length === 0) {
        list.innerHTML = `
          <div class="routes-empty">
            <div class="empty-state-icon">${svgIcon("i-route")}</div>
            <span>Nessun percorso trovato per questo mezzo.</span>
          </div>`;
        return;
    }

    list.innerHTML = filtered
        .map((r) => {
            const label = modeLabel[r.mode] || r.mode;
            const icon = modeIcon[r.mode] || svgIcon("i-car");
            const badge = modeBadge[r.mode] || "car";

            return `
        <div class="route-card" data-mode="${r.mode}" data-id="${r.id}">
          <div class="route-card-icon">${icon}</div>
          <div class="route-card-info">
            <div class="route-card-title">${escapeHtml(r.from)} → ${escapeHtml(r.to)}</div>
            <div class="route-card-meta">
              <span><strong>${r.date || "--"}</strong></span>
              <span><strong>${r.distanceKm || "--"} km</strong></span>
              <span><strong>${r.durationMin || "--"} min</strong></span>
              <span class="route-badge ${badge}">${label}</span>
            </div>
          </div>
          <div class="route-card-actions">
            <button class="btn-repeat" type="button" data-action="repeat-route" data-id="${r.id}">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24"
                   fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
              Ripeti
            </button>
          </div>
        </div>`;
        })
        .join("");
}

async function loadRoutes() {
    try {
        const res = await fetch("/api/users/routes");
        if (!res.ok) throw new Error("Errore nel caricamento dei percorsi");
        const data = await res.json();

        userRoutes = data.map(r => ({
            id: r.id,
            mode: r.mode,
            from: r.start_address,
            to: r.end_address,
            startaddress: r.start_address,
            endaddress: r.end_address,
            distanceKm: r.distance_km != null ? r.distance_km.toFixed(1) : null,
            durationMin: r.duration_min != null ? Math.round(r.duration_min) : null,
            date: r.updated_at ? new Date(r.updated_at).toLocaleDateString("it-IT") : null
        }));

        percorsiLoaded = true;
        renderRoutes(userRoutes, currentFilter);
        renderRecentRoutes();
    } catch (err) {
        console.error("Errore fetch percorsi:", err);
    }
}

function getUserRouteById(routeId) {
    return userRoutes.find((r) => String(r.id) === String(routeId));
}

function repeatRoute(route) {
    if (!route) return;
    const params = new URLSearchParams({
        startaddress: route.startaddress,
        endaddress: route.endaddress,
        routemode: route.mode,
    });
    window.location.href = `/logged/map?${params.toString()}`;
}

function renderRouteDetailsModal(route) {
    const content = document.getElementById("routeDetailsContent");
    const label = modeLabel[route.mode] || route.mode;
    const icon = modeIcon[route.mode] || svgIcon("i-car");

    content.innerHTML = `
      <div class="pro-rows">
        <div class="pro-row"><span class="pro-lbl">Partenza</span><span class="pro-val">${escapeHtml(route.from)}</span></div>
        <div class="pro-row"><span class="pro-lbl">Destinazione</span><span class="pro-val">${escapeHtml(route.to)}</span></div>
        <div class="pro-row"><span class="pro-lbl">Mezzo</span><span class="pro-val">${icon} ${label}</span></div>
        <div class="pro-row"><span class="pro-lbl">Distanza</span><span class="pro-val">${route.distanceKm || "--"} km</span></div>
        <div class="pro-row"><span class="pro-lbl">Durata</span><span class="pro-val">${route.durationMin || "--"} min</span></div>
        <div class="pro-row"><span class="pro-lbl">Data</span><span class="pro-val">${route.date || "--"}</span></div>
      </div>
      <button class="co-map-btn" type="button" data-action="repeat-route" data-id="${route.id}">
        <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24"
             fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
        Ripeti
      </button>
    `;
}

function openRouteDetails(routeId) {
    const route = getUserRouteById(routeId);
    const overlay = document.getElementById("routeDetailsOverlay");
    if (!route || !overlay) return;

    renderRouteDetailsModal(route);
    overlay.classList.add("active");
}

function closeRouteDetails() {
    const overlay = document.getElementById("routeDetailsOverlay");
    if (!overlay) return;
    overlay.classList.remove("active");
}

function goToMap(companyId) {
    const c = getCompanyById(companyId);
    if (!c) return;
    const params = new URLSearchParams({
        startaddress: "Bergamo, BG",
        endaddress: c.address,
        endname: c.name,
        routemode: "driving-car",
    });
    window.location.href = `/logged/map?${params.toString()}`;
}

function renderRecentRoutes() {
    const list = document.getElementById("recentRoutesList");
    if (!userRoutes || userRoutes.length === 0) {
        list.innerHTML = `
            <div class="route-item">
                <div class="route-info">Nessun percorso salvato</div>
            </div>`;
        return;
    }

    const recent = userRoutes.slice(0, 3);

    list.innerHTML = recent
        .map(
            (r) => `
      <div class="route-item" data-id="${r.id}">
        <div class="route-icon">${modeIcon[r.mode] || svgIcon("i-car")}</div>
        <div class="route-info">
          <div class="route-from-to">${escapeHtml(r.from)} → ${escapeHtml(r.to)}</div>
          <div class="route-meta">${r.date || "--"} · ${r.distanceKm || "--"} km · ${r.durationMin || "--"} min</div>
        </div>
        <span class="route-badge ${modeBadge[r.mode] || "car"}">${modeLabel[r.mode] || "Auto"}</span>
      </div>`,
        )
        .join("");
}

const EMPTY_PROFILO_DATA = {
    name: "",
    surname: "",
    email: "",
    data_nascita: "",
    sesso: "",
    comune_nascita: "",
    codice_fiscale: "",
    telefono: "",
    indirizzo_studio: "",
    classe: "",
    indirizzo: "",
    picture: "",
    istituto: "",
    skills: [],
    soft_skills: [],
    languages: [],
    experiences: [],
};
let profiloData = { ...EMPTY_PROFILO_DATA };
let profiloLoaded = false;

const ALL_SOFT_SKILLS = [
    { icon: "i-brain", label: "Problem solving" },
    { icon: "i-user", label: "Lavoro in team" },
    { icon: "i-route", label: "Gestione del tempo" },
    { icon: "i-bell", label: "Comunicazione" },
    { icon: "i-pin", label: "Attenzione ai dettagli" },
    { icon: "i-palette", label: "Creatività" },
    { icon: "i-bell", label: "Public speaking" },
    { icon: "i-route", label: "Adattabilità" },
    { icon: "i-globe", label: "Leadership" },
    { icon: "i-graduate", label: "Autoapprendimento" },
];

const SKILL_LV_MAP = { Base: 33, Intermedio: 65, Avanzato: 90 };
const SKILL_LV_DB_MAP = { Base: 1, Intermedio: 2, Avanzato: 3 };
const SKILL_LV_LABEL_MAP = { 1: "Base", 2: "Intermedio", 3: "Avanzato" };
const LANGUAGE_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"];

function sanitizeUrl(url) {
    const value = String(url || "").trim();
    if (!value) return "";

    if (/^(https?:)?\/\//i.test(value)) return value;
    if (/^[a-z][a-z0-9+.-]*:/i.test(value)) return "";

    return `https://${value}`;
}

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    })[char]);
}

function normalizeDateInput(value) {
    if (!value) return "";

    if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}/.test(value)) {
        return value.slice(0, 10);
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) return "";

    return date.toISOString().slice(0, 10);
}

function normalizeSkillLevel(value) {
    return SKILL_LV_LABEL_MAP[value] || value || "Base";
}

function splitIndirizzo(value) {
    if (Array.isArray(value)) {
        return value.map((part) => String(part || "").trim());
    }

    return String(value || "")
        .split("££")
        .map((part) => part.trim());
}

function splitLabels(value) {
    if (Array.isArray(value)) return value.map((v) => String(v || "").trim()).filter(Boolean);

    return String(value || "")
        .split("££")
        .map((label) => label.trim())
        .filter(Boolean);
}

function getComuneResidenza(indirizzo) {
    return splitIndirizzo(indirizzo)[3] || "";
}

function normalizeProfiloData(data) {
    return {
        ...EMPTY_PROFILO_DATA,
        ...data,
        data_nascita:
            data.data_nascita === undefined
                ? EMPTY_PROFILO_DATA.data_nascita
                : normalizeDateInput(data.data_nascita),
        skills: Array.isArray(data.skills)
            ? data.skills.map((skill) => ({
                name: skill.name || "",
                livello: normalizeSkillLevel(skill.livello),
            }))
            : [],
        soft_skills: Array.isArray(data.soft_skills)
            ? data.soft_skills.map((soft) => ({
                label: soft.label || "",
                icon: soft.icon || "i-brain",
            }))
            : [],
        languages: Array.isArray(data.languages)
            ? data.languages.map((l) => ({
                name: l.name || "",
                level: l.level || "A1",
                certification: l.certification || "",
            }))
            : [],
        experiences: Array.isArray(data.experiences)
            ? data.experiences.map((e) => ({
                title: e.title || "",
                link: e.link || "",
                description: e.description || "",
                labels: splitLabels(e.labels),
            }))
            : [],
    };
}

function setProfiloEditEnabled(enabled) {
    const btn = document.getElementById("btnEditProfilo");

    if (!btn) return;

    btn.disabled = !enabled;
    btn.setAttribute("aria-busy", String(!enabled));
}

function renderProfiloLoading() {
    setProfiloEditEnabled(false);

    document.querySelector(".profilo-hero-name").textContent = "Caricamento profilo";
    document.querySelector(".profilo-hero-sub").textContent = "Recupero dati in corso...";

    const loadingState = `
        <div class="section-state profile-state">
            <div class="spinner"></div>
            <span>Caricamento dati profilo...</span>
        </div>
    `;

    const anagraficaEl = document.getElementById("proAnagrafica");
    const scuolaEl = document.getElementById("proScuola");
    const skillsEl = document.getElementById("proSkills");
    const softEl = document.getElementById("proSoftSkills");

    if (anagraficaEl) anagraficaEl.innerHTML = loadingState;
    if (scuolaEl) scuolaEl.innerHTML = loadingState;
    if (skillsEl) skillsEl.innerHTML = loadingState;
    if (softEl) softEl.innerHTML = loadingState;
}

function renderProfiloError() {
    setProfiloEditEnabled(false);

    document.querySelector(".profilo-hero-name").textContent = "Profilo non disponibile";
    document.querySelector(".profilo-hero-sub").textContent = "Impossibile recuperare i dati profilo.";

    const errorState = `
        <div class="section-state profile-state">
            <span>Errore nel caricamento del profilo. Ricarica la pagina.</span>
        </div>
    `;

    const anagraficaEl = document.getElementById("proAnagrafica");
    const scuolaEl = document.getElementById("proScuola");
    const skillsEl = document.getElementById("proSkills");
    const softEl = document.getElementById("proSoftSkills");

    if (anagraficaEl) anagraficaEl.innerHTML = errorState;
    if (scuolaEl) scuolaEl.innerHTML = errorState;
    if (skillsEl) skillsEl.innerHTML = errorState;
    if (softEl) softEl.innerHTML = errorState;
}

async function loadProfiloData() {
    renderProfiloLoading();

    try {
        const response = await fetch("/api/users/profile");

        if (!response.ok) throw new Error(`[ERROR] http code ${response.status}`);

        const data = await response.json();
        profiloData = normalizeProfiloData(data || {});
        profiloLoaded = true;
        updateProfiloUI(null);
        setProfiloEditEnabled(true);
    } catch (err) {
        console.error("Errore caricamento profilo:", err);
        profiloLoaded = false;
        renderProfiloError();
    }
}

function openProfiloModal() {
    if (!profiloLoaded) {
        showToast("Attendi il caricamento del profilo");

        return;
    }

    renderSkillsEditor();

    renderSoftEditor();

    renderLangEditor();

    renderExpEditor();

    setApiStatus("", "");

    document.getElementById("profiloOverlay").classList.add("active");
    switchTab("skills");
}

function closeProfiloModal() {
    document.getElementById("profiloOverlay").classList.remove("active");
}

function switchTab(name) {
    document.querySelectorAll(".pro-tab").forEach((t) => {
        t.classList.toggle("active", t.dataset.tab === name);
    });
    document.querySelectorAll(".pro-tab-panel").forEach((p) => {
        p.classList.toggle(
            "active",
            p.id === "tab" + name.charAt(0).toUpperCase() + name.slice(1),
        );
    });
}

function renderSkillsEditor() {
    const el = document.getElementById("proSkillsEditor");
    el.innerHTML = profiloData.skills
        .map((s, i) => `
            <div class="pro-skill-edit-row">
                <input type="text" value="${escapeHtml(s.name)}" placeholder="Es. Python" data-skill-index="${i}" data-skill-field="name"/>
                <select data-skill-index="${i}" data-skill-field="livello">
                    ${["Base", "Intermedio", "Avanzato"]
                    .map((lv) =>
                        `<option value="${lv}"${s.livello === lv ? " selected" : ""}>${lv}</option>`,
                    ).join("")}
                </select>
                <button class="pro-del-btn" data-skill-remove="${i}">✕</button>
            </div>
        `).join("");
}

function addSkillRow() {
    profiloData.skills.push({ name: "", livello: "Base" });
    renderSkillsEditor();
}

function removeSkill(i) {
    profiloData.skills.splice(i, 1);
    renderSkillsEditor();
}

function renderSoftEditor() {
    const el = document.getElementById("proSoftEditor");
    el.innerHTML = ALL_SOFT_SKILLS.map((s) => {
        const sel = profiloData.soft_skills.some((soft) => soft.label === s.label);
        return `
        <div class="pro-soft-check${sel ? " selected" : ""}" onclick="toggleSoft(this, '${s.label}')">
          <input type="checkbox"${sel ? " checked" : ""}/>
          <span class="pro-soft-check-icon">${svgIcon(s.icon)}</span>
          <span class="pro-soft-check-label">${s.label}</span>
        </div>`;
    }).join("");
}

function toggleSoft(el, label) {
    el.classList.toggle("selected");
    const idx = profiloData.soft_skills.findIndex((soft) => soft.label === label);
    if (idx === -1) {
        const found = ALL_SOFT_SKILLS.find((soft) => soft.label === label);
        profiloData.soft_skills.push({
            label,
            icon: found ? found.icon : "i-brain",
        });
    } else {
        profiloData.soft_skills.splice(idx, 1);
    }
}

function renderLangEditor() {
    const el = document.getElementById("proLangEditor");
    el.innerHTML = profiloData.languages
        .map((l, i) => `
            <div class="pro-skill-edit-row">
                <input type="text" value="${escapeHtml(l.name)}" placeholder="Es. Inglese" data-lang-index="${i}" data-lang-field="name"/>
                <select data-lang-index="${i}" data-lang-field="level">
                    ${LANGUAGE_LEVELS
                    .map((lv) =>
                        `<option value="${lv}"${l.level === lv ? " selected" : ""}>${lv}</option>`,
                    ).join("")}
                </select>
                <input type="text" value="${escapeHtml(l.certification)}" placeholder="Certificazione (opz.)" data-lang-index="${i}" data-lang-field="certification"/>
                <button class="pro-del-btn" data-lang-remove="${i}">✕</button>
            </div>
        `).join("");
}

function addLangRow() {
    profiloData.languages.push({ name: "", level: "A1", certification: "" });
    renderLangEditor();
}

function removeLang(i) {
    profiloData.languages.splice(i, 1);
    renderLangEditor();
}

function renderExpEditor() {
    const el = document.getElementById("proExpEditor");
    el.innerHTML = profiloData.experiences
        .map((e, i) => `
            <div class="pro-exp-edit-row" data-exp-index="${i}">
                <input type="text" value="${escapeHtml(e.title)}" placeholder="Titolo (es. Stage — TechLab Srl)" data-exp-index="${i}" data-exp-field="title"/>
                <input type="text" value="${escapeHtml(e.link)}" placeholder="Link (opzionale)" data-exp-index="${i}" data-exp-field="link"/>
                <textarea placeholder="Breve descrizione" data-exp-index="${i}" data-exp-field="description">${escapeHtml(e.description)}</textarea>
                <div class="pro-exp-labels-editor">
                    ${e.labels
                    .map((label, li) => `
                        <span class="pro-chip">${escapeHtml(label)}<button type="button" class="pro-chip-remove" data-exp-index="${i}" data-label-remove="${li}">✕</button></span>
                    `).join("")}
                    <input type="text" class="pro-chip-input" placeholder="Aggiungi etichetta e premi Invio" data-exp-label-input="${i}"/>
                </div>
                <button class="pro-del-btn" data-exp-remove="${i}">✕ Rimuovi esperienza</button>
            </div>
        `).join("");
}

function addExpRow() {
    profiloData.experiences.push({ title: "", link: "", description: "", labels: [] });
    renderExpEditor();
}

function removeExp(i) {
    profiloData.experiences.splice(i, 1);
    renderExpEditor();
}

function addExpLabel(expIndex, text) {
    const label = String(text || "").trim();
    if (!label) return;

    const exp = profiloData.experiences[expIndex];
    const alreadyPresent = exp.labels.some((l) => l.toLowerCase() === label.toLowerCase());
    if (!alreadyPresent) exp.labels.push(label);

    renderExpEditor();
}

function removeExpLabel(expIndex, labelIndex) {
    profiloData.experiences[expIndex].labels.splice(labelIndex, 1);
    renderExpEditor();
}

function setApiStatus(msg, cls) {
    const el = document.getElementById("proApiStatus");
    el.textContent = msg;
    el.className =
        "pro-api-status" +
        (msg ? " show" : "") +
        (cls ? " " + cls : "");
}

function buildProfiloPayload() {
    return {
        skills: profiloData.skills
            .filter((skill) => String(skill.name || "").trim())
            .map((skill) => ({
                name: String(skill.name || "").trim(),
                livello: SKILL_LV_DB_MAP[skill.livello] || skill.livello,
            })),
        soft_skills: profiloData.soft_skills.map((soft) => ({
            label: soft.label,
            icon: soft.icon || "i-brain",
        })),
        languages: profiloData.languages
            .filter((l) => String(l.name || "").trim())
            .map((l) => ({
                name: String(l.name).trim(),
                level: l.level,
                certification: String(l.certification || "").trim() || null,
            })),
        experiences: profiloData.experiences
            .filter((e) => String(e.title || "").trim())
            .map((e) => ({
                title: String(e.title).trim(),
                link: String(e.link || "").trim() || null,
                description: String(e.description || "").trim() || null,
                labels: e.labels || [],
            })),
    };
}

async function salvaProfilo() {
    const payload = buildProfiloPayload();
    const btn = document.getElementById("btnSalvaProfilo");
    btn.textContent = "Salvataggio...";
    btn.disabled = true;
    setApiStatus("Salvataggio in corso…", "");

    try {
        const response = await fetch("/api/users/profile/save", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error(`[ERROR] http code ${response.status}`);

        const result = await response.json();

        if (result.user) {
            profiloData = normalizeProfiloData(result.user);
        }

        updateProfiloUI(null);
        setApiStatus("Profilo aggiornato", "ok");
        setTimeout(closeProfiloModal, 1000);
    } catch (err) {
        console.error("Errore salvataggio profilo:", err);
        setApiStatus("Errore nel salvataggio. Riprova.", "err");
    } finally {
        btn.textContent = "Salva modifiche";
        btn.disabled = false;
    }
}

function updateProfiloUI(apiResult) {
    // Nome hero
    document.querySelector(".profilo-hero-name").textContent = profiloData.name + " " + profiloData.surname;
    document.querySelector(".profilo-hero-sub").textContent = `Studente · ${profiloData.classe || ""} · ${profiloData.istituto || ""}, Bergamo`;
    const sidebarRole = document.querySelector(".user-role");

    if (sidebarRole) {
        sidebarRole.textContent = `Studente · ${profiloData.classe || ""}`;
    }

    const anagraficaEl = document.getElementById("proAnagrafica");
    if (anagraficaEl) {
        anagraficaEl.innerHTML = `
            <div class="pro-row"><span class="pro-lbl">Nome</span><span class="pro-val">${escapeHtml(profiloData.name)}</span></div>
            <div class="pro-row"><span class="pro-lbl">Cognome</span><span class="pro-val">${escapeHtml(profiloData.surname)}</span></div>
            <div class="pro-row"><span class="pro-lbl">Data di nascita</span><span class="pro-val">${escapeHtml(profiloData.data_nascita)}</span></div>
            <div class="pro-row"><span class="pro-lbl">Codice fiscale</span><span class="pro-val pro-mono">${escapeHtml(profiloData.codice_fiscale)}</span></div>
            <div class="pro-row"><span class="pro-lbl">Comune di residenza</span><span class="pro-val">${escapeHtml(getComuneResidenza(profiloData.indirizzo))}</span></div>
            <div class="pro-row"><span class="pro-lbl">Telefono</span><span class="pro-val">${escapeHtml(profiloData.telefono)}</span></div>
            <div class="pro-row"><span class="pro-lbl">Email</span><span class="pro-val">${escapeHtml(profiloData.email)}</span></div>`;
    }

    const scuolaEl = document.getElementById("proScuola");
    if (scuolaEl) {
        scuolaEl.innerHTML = `
            <div class="pro-row"><span class="pro-lbl">Istituto</span><span class="pro-val">${escapeHtml(profiloData.istituto)}</span></div>
            <div class="pro-row"><span class="pro-lbl">Indirizzo</span><span class="pro-val">${escapeHtml(profiloData.indirizzo_studio)}</span></div>
            <div class="pro-row"><span class="pro-lbl">Classe</span><span class="pro-val">${escapeHtml(profiloData.classe)}</span></div>`;
    }

    // Aggiorna suggerimento come tag (se presente)
    if (apiResult && apiResult.suggerimento) {
        const tagsEl = document.querySelector(".profilo-hero-tags");
        const existing = tagsEl.querySelector(".pro-tag-suggerimento");
        if (existing) existing.remove();
        const tag = document.createElement("span");
        tag.className = "pro-tag pro-tag-suggerimento";
        tag.textContent = apiResult.suggerimento;
        tagsEl.appendChild(tag);
    }

    const skillsEl = document.getElementById("proSkills");
    if (skillsEl) {
        skillsEl.innerHTML = profiloData.skills
            .filter((s) => s.name)
            .map((s) => {
                const pct = SKILL_LV_MAP[s.livello] || 50;
                return `
                    <div class="pro-skill-row">
                        <span class="pro-skill-name">${escapeHtml(s.name)}</span>
                        <div class="pro-skill-bar"><div class="pro-skill-fill" style="width:${pct}%"></div></div>
                        <span class="pro-skill-lv">${escapeHtml(s.livello)}</span>
                    </div>
                `;
            })
            .join("");
    }

    const softEl = document.getElementById("proSoftSkills");
    if (softEl) {
        softEl.innerHTML = profiloData.soft_skills
            .map((soft) => {
                return `
                    <div class="pro-soft-item">
                      <span class="pro-soft-icon">${svgIcon(soft.icon || "i-brain")}</span>
                      <span>${escapeHtml(soft.label)}</span>
                    </div>
                `;
            })
            .join("");
    }

    const linguaEl = document.getElementById("proLingue");
    if (linguaEl) {
        linguaEl.innerHTML = profiloData.languages
            .map((l) => `
                <div class="pro-row">
                    <span class="pro-lbl">${escapeHtml(l.name)}</span>
                    <span class="pro-val"><span class="pro-badge">${escapeHtml(l.level)}</span>${l.certification ? " " + escapeHtml(l.certification) : ""}</span>
                </div>
            `)
            .join("") || `<div class="section-state profile-state"><span>Nessuna lingua inserita.</span></div>`;
    }

    const espEl = document.getElementById("proEsperienze");
    if (espEl) {
        espEl.innerHTML = profiloData.experiences
            .map((e) => {
                const safeLink = sanitizeUrl(e.link);
                const title = safeLink
                    ? `<a href="${escapeHtml(safeLink)}" target="_blank" rel="noopener noreferrer">${escapeHtml(e.title)}</a>`
                    : escapeHtml(e.title);
                const labels = e.labels
                    .map((label) => `<span class="pro-badge">${escapeHtml(label)}</span>`)
                    .join("");

                return `
                    <div class="pro-exp-item">
                        <div class="pro-exp-dot"></div>
                        <div class="pro-exp-body">
                            <div class="pro-exp-title">${title}</div>
                            ${e.description ? `<div class="pro-exp-desc">${escapeHtml(e.description)}</div>` : ""}
                            ${labels ? `<div class="pro-exp-labels">${labels}</div>` : ""}
                        </div>
                    </div>
                `;
            })
            .join("") || `<div class="section-state profile-state"><span>Nessuna esperienza inserita.</span></div>`;
    }
}

let impostazioniData = {
    notifMatch: true,
    notifPercorsi: true,
    notifScuola: true,
    notifScadenze: false,
    notifEmail: true,
    privVisibilita: "school",
    privCondividi: true,
    privLink: false,
    tema: "dark",
    mezzoDefault: "driving-car",
    lingua: "it",
    reduceMotion: false,
};

function saveImpostazioni() {
    impostazioniData.notifMatch =
        document.getElementById("notifMatch")?.checked;
    impostazioniData.notifPercorsi =
        document.getElementById("notifPercorsi")?.checked;
    impostazioniData.notifScuola =
        document.getElementById("notifScuola")?.checked;
    impostazioniData.notifScadenze =
        document.getElementById("notifScadenze")?.checked;
    impostazioniData.notifEmail =
        document.getElementById("notifEmail")?.checked;
    impostazioniData.privVisibilita =
        document.getElementById("privVisibilita")?.value;
    impostazioniData.privCondividi =
        document.getElementById("privCondividi")?.checked;
    impostazioniData.privLink = document.getElementById("privLink")?.checked;
    impostazioniData.mezzoDefault =
        document.getElementById("mezzoDefault")?.value;
    impostazioniData.lingua = document.getElementById("lingua")?.value;
    impostazioniData.reduceMotion =
        document.getElementById("reduceMotion")?.checked;
    showToast("Impostazione salvata");
}

function setTema(btn) {
    document
        .querySelectorAll(".imp-seg")
        .forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    impostazioniData.tema = btn.dataset.val;
    showToast("Tema aggiornato");
}

function closeImpModal() {
    document.getElementById("impOverlay").classList.remove("active");
}

function salvaImpModal() {
    saveImpostazioni();
    closeImpModal();
}

let toastTimer;
function showToast(msg) {
    const t = document.getElementById("impToast");
    if (!t) return;
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 2200);
}

let notifications = [];

function loadNotificationsData() {
    const el = document.getElementById("notifications-data");
    if (!el) return;
    try {
        notifications = JSON.parse(el.textContent) || [];
    } catch {
        notifications = [];
    }
}

function formatNotifTime(iso) {
    const date = new Date(iso);
    if (isNaN(date)) return "";
    return date.toLocaleString("it-IT", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function renderNotifications() {
    const list = document.getElementById("notifList");
    const empty = document.getElementById("notifEmpty");
    const badge = document.getElementById("notifBadge");
    if (!list || !empty || !badge) return;

    const unreadCount = notifications.filter((n) => !n.is_read).length;
    badge.textContent = String(unreadCount);
    badge.classList.toggle("hidden", unreadCount === 0);

    if (notifications.length === 0) {
        list.innerHTML = "";
        empty.classList.remove("hidden");
        return;
    }

    empty.classList.add("hidden");
    list.innerHTML = notifications
        .map(
            (n) => `
        <div class="notif-item ${n.is_read ? "read" : "unread"}" data-notif-id="${n.id}">
            <div class="notif-item-dot"></div>
            <div class="notif-item-body">
                <div class="notif-item-top">
                    <span class="notif-item-title">${escapeHtml(n.title)}</span>
                    <span class="notif-item-time">${formatNotifTime(n.created_at)}</span>
                </div>
                ${n.sender ? `<div class="notif-item-sender">${escapeHtml(n.sender)}</div>` : ""}
                <div class="notif-item-message">${escapeHtml(n.message)}</div>
                ${
                    !n.is_read
                        ? `<div class="notif-item-footer">
                        <button class="notif-item-check" type="button" title="Segna come letta" data-notif-check="${n.id}">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 4 4 10-10"/></svg>
                        </button>
                    </div>`
                        : ""
                }
            </div>
        </div>`,
        )
        .join("");
}

function openNotifDetails(id) {
    const notif = notifications.find((n) => n.id === id);
    const overlay = document.getElementById("notifDetailsOverlay");
    if (!notif || !overlay) return;

    document.getElementById("notifDetailsTitle").textContent = notif.title;
    document.getElementById("notifDetailsMeta").textContent = notif.sender
        ? `${notif.sender} · ${formatNotifTime(notif.created_at)}`
        : formatNotifTime(notif.created_at);
    document.getElementById("notifDetailsMessage").textContent = notif.message;

    overlay.classList.add("active");
    markNotificationRead(id);
}

function closeNotifDetails() {
    const overlay = document.getElementById("notifDetailsOverlay");
    if (!overlay) return;
    overlay.classList.remove("active");
}

async function markNotificationRead(id) {
    const notif = notifications.find((n) => n.id === id);
    if (!notif || notif.is_read) return;

    notif.is_read = true;
    renderNotifications();

    try {
        await fetch("/api/users/notifications/read", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notification_id: id }),
        });
    } catch {
        // Stato locale già aggiornato; un eventuale errore di rete non blocca la UI.
    }
}

function toggleNotifPanel() {
    const panel = document.getElementById("notifPanel");
    const btn = document.getElementById("notificationsToggle");
    if (!panel || !btn) return;
    const isActive = panel.classList.toggle("active");
    btn.setAttribute("aria-expanded", String(isActive));
}

function closeNotifPanel() {
    const panel = document.getElementById("notifPanel");
    const btn = document.getElementById("notificationsToggle");
    if (!panel || !btn) return;
    panel.classList.remove("active");
    btn.setAttribute("aria-expanded", "false");
}

function esportaDati() {
    const payload = {
        profilo: profiloData,
        impostazioni: impostazioniData,
        esportato: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json",
    });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "stagematch_dati.json";
    a.click();
    showToast("Download avviato");
}

function esportaCV() {
    showToast("Generazione PDF in corso...");
    setTimeout(() => showToast("CV pronto per il download"), 1800);
}

function openLogoutModal() {
    document.getElementById("logoutOverlay").classList.add("active");
    document.getElementById("logoutCancel").focus();
}

function closeLogoutModal() {
    document.getElementById("logoutOverlay").classList.remove("active");
}

function toggleSidebar() {
    document.getElementById("sidebar").classList.toggle("open");
    document.getElementById("overlay").classList.toggle("active");
}

function closeSidebar() {
    document.getElementById("sidebar").classList.remove("open");
    document.getElementById("overlay").classList.remove("active");
}

document.addEventListener("DOMContentLoaded", () => {
    loadRoutes();
    loadNotificationsData();
    renderNotifications();
    loadProfiloData();
    aziendeLoaded = true;
    loadCompanies();

    document.getElementById("overlay").addEventListener("click", closeSidebar);

    document
        .querySelector(".hamburger")
        .addEventListener("click", toggleSidebar);

    document.getElementById("navDashboard").addEventListener("click", (e) => {
        e.preventDefault();
        showSection("dashboard");
        setActive(e.currentTarget);
    });
    document.getElementById("navPercorsi").addEventListener("click", (e) => {
        e.preventDefault();
        showSection("percorsi");
        setActive(e.currentTarget);
    });
    document.getElementById("navAziende").addEventListener("click", (e) => {
        e.preventDefault();
        showSection("aziende");
        setActive(e.currentTarget);
    });
    document.getElementById("navProfilo").addEventListener("click", (e) => {
        e.preventDefault();
        showSection("profilo");
        setActive(e.currentTarget);
    });
    document.getElementById("profiloButton").addEventListener("click", (e) => {
        e.preventDefault();
        showSection("profilo");
        setActive(document.getElementById("navProfilo"));
    });
    document
        .getElementById("navImpostazioni")
        .addEventListener("click", (e) => {
            e.preventDefault();
            showSection("impostazioni");
            setActive(e.currentTarget);
        });
    document.getElementById("navLogout").addEventListener("click", (e) => {
        e.preventDefault();
        openLogoutModal();
    });

    document.getElementById("aziendeList").addEventListener("click", (e) => {
        const applyButton = e.target.closest('[data-action="apply-offer"]');
        if (applyButton) {
            if (!applyButton.disabled) applyToOffer(applyButton.dataset.companyId);
            return;
        }

        const detailsButton = e.target.closest('[data-action="open-company-details"]');
        if (detailsButton) {
            openCompanyDetails(detailsButton.dataset.companyId);
            return;
        }

        const companyCard = e.target.closest(".co-card");
        if (companyCard) openCompanyDetails(companyCard.dataset.id);
    });

    document
        .getElementById("companyDetailsClose")
        .addEventListener("click", closeCompanyDetails);
    document
        .getElementById("companyDetailsOverlay")
        .addEventListener("click", (e) => {
            if (e.target === e.currentTarget) closeCompanyDetails();
        });
    document
        .getElementById("companyDetailsContent")
        .addEventListener("click", async (e) => {
            const mapButton = e.target.closest('[data-action="go-to-company-map"]');
            if (mapButton) {
                goToMap(mapButton.dataset.companyId);
                return;
            }

            const applyButton = e.target.closest('[data-action="apply-offer"]');
            if (applyButton && !applyButton.disabled) {
                await applyToOffer(applyButton.dataset.companyId);
                const company = getCompanyById(applyButton.dataset.companyId);
                if (company) renderCompanyDetailsModal(company);
            }
        });
    document.addEventListener("keydown", (e) => {
        if (
            e.key === "Escape" &&
            document
                .getElementById("companyDetailsOverlay")
                .classList.contains("active")
        ) {
            closeCompanyDetails();
        }
    });

    document.getElementById("btnDashAziende").addEventListener("click", () => {
        showSection("aziende");
        setActive(document.getElementById("navAziende"));
    });
    function goToPercorsiSection() {
        showSection("percorsi");
        setActive(document.getElementById("navPercorsi"));
    }

    document
        .getElementById("btnVediPercorsi")
        .addEventListener("click", goToPercorsiSection);

    document.getElementById("recentRoutesList").addEventListener("click", (e) => {
        if (e.target.closest(".route-item")) goToPercorsiSection();
    });

    document.getElementById("percorsiList").addEventListener("click", (e) => {
        const repeatButton = e.target.closest('[data-action="repeat-route"]');
        if (repeatButton) {
            repeatRoute(getUserRouteById(repeatButton.dataset.id));
            return;
        }

        const card = e.target.closest(".route-card");
        if (card) openRouteDetails(card.dataset.id);
    });

    document
        .getElementById("routeDetailsClose")
        .addEventListener("click", closeRouteDetails);
    document
        .getElementById("routeDetailsOverlay")
        .addEventListener("click", (e) => {
            if (e.target === e.currentTarget) closeRouteDetails();
        });
    document
        .getElementById("routeDetailsContent")
        .addEventListener("click", (e) => {
            const repeatButton = e.target.closest('[data-action="repeat-route"]');
            if (repeatButton) repeatRoute(getUserRouteById(repeatButton.dataset.id));
        });
    document.addEventListener("keydown", (e) => {
        if (
            e.key === "Escape" &&
            document
                .getElementById("routeDetailsOverlay")
                .classList.contains("active")
        ) {
            closeRouteDetails();
        }
    });

    const notificationsToggle = document.getElementById("notificationsToggle");
    if (notificationsToggle) {
        notificationsToggle.addEventListener("click", (e) => {
            e.stopPropagation();
            toggleNotifPanel();
        });
    }

    const notifList = document.getElementById("notifList");
    if (notifList) {
        notifList.addEventListener("click", (e) => {
            const checkBtn = e.target.closest("[data-notif-check]");
            if (checkBtn) {
                e.stopPropagation();
                markNotificationRead(Number(checkBtn.dataset.notifCheck));
                return;
            }

            const item = e.target.closest(".notif-item");
            if (!item) return;

            openNotifDetails(Number(item.dataset.notifId));
        });
    }

    const notifDetailsOverlay = document.getElementById("notifDetailsOverlay");
    if (notifDetailsOverlay) {
        document
            .getElementById("notifDetailsClose")
            .addEventListener("click", closeNotifDetails);
        notifDetailsOverlay.addEventListener("click", (e) => {
            if (e.target === e.currentTarget) closeNotifDetails();
        });
    }

    document.addEventListener("click", (e) => {
        const wrap = document.getElementById("notifWrap");
        if (wrap && !wrap.contains(e.target)) closeNotifPanel();
    });

    const heroGoToMapBtn = document.getElementById("heroGoToMapBtn");

    function updateHeroMapLink(mode) {
        if (!heroGoToMapBtn) return;
        const params = new URLSearchParams({ routemode: mode });
        heroGoToMapBtn.href = `${heroGoToMapBtn.getAttribute("href").split("?")[0]}?${params.toString()}`;
    }

    document.querySelectorAll(".t-pill").forEach((pill) => {
        pill.addEventListener("click", () => {
            document
                .querySelectorAll(".t-pill")
                .forEach((p) => p.classList.remove("active"));
            pill.classList.add("active");
            updateHeroMapLink(pill.dataset.mode);
        });
    });

    const activePill = document.querySelector(".t-pill.active");
    if (activePill) updateHeroMapLink(activePill.dataset.mode);

    document.querySelectorAll(".filter-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            document
                .querySelectorAll(".filter-btn")
                .forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            currentFilter = btn.dataset.filter;
            if (percorsiLoaded) renderRoutes(userRoutes, currentFilter);
        });
    });

    document
        .getElementById("btnEditProfilo")
        .addEventListener("click", openProfiloModal);

    document.querySelectorAll(".pro-tab").forEach((tab) => {
        tab.addEventListener("click", () => switchTab(tab.dataset.tab));
    });

    document
        .querySelector("#profiloOverlay .profilo-modal-close")
        .addEventListener("click", closeProfiloModal);

    document
        .getElementById("btnAddSkill")
        .addEventListener("click", addSkillRow);

    document.getElementById("proSkillsEditor").addEventListener("change", (e) => {
        const { skillIndex, skillField } = e.target.dataset;
        if (skillIndex === undefined || !skillField) return;

        profiloData.skills[Number(skillIndex)][skillField] = e.target.value;
    });
    document.getElementById("proSkillsEditor").addEventListener("click", (e) => {
        const removeButton = e.target.closest("[data-skill-remove]");
        if (!removeButton) return;

        removeSkill(Number(removeButton.dataset.skillRemove));
    });

    document
        .getElementById("btnAddLanguage")
        .addEventListener("click", addLangRow);

    document.getElementById("proLangEditor").addEventListener("change", (e) => {
        const { langIndex, langField } = e.target.dataset;
        if (langIndex === undefined || !langField) return;

        profiloData.languages[Number(langIndex)][langField] = e.target.value;
    });
    document.getElementById("proLangEditor").addEventListener("click", (e) => {
        const removeButton = e.target.closest("[data-lang-remove]");
        if (!removeButton) return;

        removeLang(Number(removeButton.dataset.langRemove));
    });

    document
        .getElementById("btnAddExperience")
        .addEventListener("click", addExpRow);

    document.getElementById("proExpEditor").addEventListener("change", (e) => {
        const { expIndex, expField } = e.target.dataset;
        if (expIndex === undefined || !expField) return;

        profiloData.experiences[Number(expIndex)][expField] = e.target.value;
    });
    document.getElementById("proExpEditor").addEventListener("keydown", (e) => {
        if (e.key !== "Enter") return;
        const expIndex = e.target.dataset.expLabelInput;
        if (expIndex === undefined) return;

        e.preventDefault();
        addExpLabel(Number(expIndex), e.target.value);
        e.target.value = "";
    });
    document.getElementById("proExpEditor").addEventListener("click", (e) => {
        const removeExpButton = e.target.closest("[data-exp-remove]");
        if (removeExpButton) {
            removeExp(Number(removeExpButton.dataset.expRemove));
            return;
        }

        const removeLabelButton = e.target.closest("[data-label-remove]");
        if (removeLabelButton) {
            removeExpLabel(
                Number(removeLabelButton.dataset.expIndex),
                Number(removeLabelButton.dataset.labelRemove),
            );
        }
    });

    document
        .querySelector("#profiloOverlay .modal-btn-cancel")
        .addEventListener("click", closeProfiloModal);
    document
        .getElementById("btnSalvaProfilo")
        .addEventListener("click", salvaProfilo);

    document.getElementById("profiloOverlay").addEventListener("click", (e) => {
        if (e.target === document.getElementById("profiloOverlay"))
            closeProfiloModal();
    });

    document
        .querySelector("#impOverlay .modal-btn-cancel")
        .addEventListener("click", closeImpModal);
    document
        .getElementById("btnSalvaImp")
        .addEventListener("click", salvaImpModal);

    document.getElementById("impOverlay").addEventListener("click", (e) => {
        if (e.target === document.getElementById("impOverlay")) closeImpModal();
    });

    document
        .getElementById("sectionImpostazioni")
        .addEventListener("change", saveImpostazioni);

    document.querySelectorAll(".imp-seg").forEach((btn) => {
        btn.addEventListener("click", () => setTema(btn));
    });

    document
        .querySelector('[data-action="esportaDati"]')
        .addEventListener("click", esportaDati);
    document
        .querySelector('[data-action="esportaCV"]')
        .addEventListener("click", esportaCV);
    document
        .querySelector('[data-action="openPrivacy"]')
        .addEventListener("click", () => {
            window.open("/privacy", "_blank", "noopener");
        });

    document
        .getElementById("logoutCancel")
        .addEventListener("click", closeLogoutModal);
    document.getElementById("logoutConfirm").addEventListener("click", () => {
        window.location.href = "/auth/logout";
    });
    document.getElementById("logoutOverlay").addEventListener("click", (e) => {
        if (e.target === document.getElementById("logoutOverlay"))
            closeLogoutModal();
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeSidebar();
            closeLogoutModal();
            closeProfiloModal();
            closeImpModal();
            closeNotifPanel();
        }
    });
});
