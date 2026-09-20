const ALL_SOFT_SKILLS = [
    { icon: "i-brain", label: "Problem solving" },
    { icon: "i-user", label: "Lavoro in team" },
    { icon: "i-users", label: "Gestione del tempo" },
    { icon: "i-bell", label: "Comunicazione" },
    { icon: "i-building", label: "Attenzione ai dettagli" },
    { icon: "i-pencil", label: "Creatività" },
    { icon: "i-bell", label: "Public speaking" },
    { icon: "i-users", label: "Adattabilità" },
    { icon: "i-building", label: "Leadership" },
    { icon: "i-pencil", label: "Autoapprendimento" },
];

const SKILL_LV_DB_MAP = { Base: 1, Intermedio: 2, Avanzato: 3 };
const SKILL_LV_LABEL_MAP = { 1: "Base", 2: "Intermedio", 3: "Avanzato" };

const APP_STATUS_LABEL = {
    inviata: "In attesa",
    vista: "In attesa",
    accettata: "Accettata",
    rifiutata: "Rifiutata",
};
const APP_STATUS_BADGE = {
    inviata: "gray",
    vista: "gray",
    accettata: "blue",
    rifiutata: "red",
};

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    })[char]);
}

function svgIcon(id, extraClass = "icon") {
    return `<span class="${extraClass}"><svg><use href="#${id}"></use></svg></span>`;
}

function initials(name, surname) {
    return `${(name || "?")[0] || ""}${(surname || "")[0] || ""}`.toUpperCase();
}

function formatDate(iso) {
    if (!iso) return "--";
    const date = new Date(iso);
    if (isNaN(date)) return "--";
    return date.toLocaleDateString("it-IT");
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

let offers = [];
let applications = [];
let notifications = [];
let annunciLoaded = false;
let candidatureLoaded = false;

let editingOfferId = null;
let offerSkills = [];
let offerSoftSkills = [];

document.addEventListener("DOMContentLoaded", () => {
    const navItems = document.querySelectorAll(".nav-item");
    const sections = document.querySelectorAll(".content");
    const hamburger = document.querySelector(".hamburger");
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");
    const logoutBtn = document.getElementById("navLogout");
    const logoutOverlay = document.getElementById("logoutOverlay");
    const logoutCancel = document.getElementById("logoutCancel");
    const logoutConfirm = document.getElementById("logoutConfirm");

    function switchSection(sectionId) {
        const targetId = "section" + sectionId;

        sections.forEach((s) => s.classList.add("hidden"));
        const target = document.getElementById(targetId);
        if (target) {
            target.classList.remove("hidden");
            target.classList.add("animate-in");
        }

        navItems.forEach((item) => {
            item.classList.toggle("active", item.id === "nav" + sectionId);
        });

        if (window.innerWidth <= 1100) {
            sidebar.classList.remove("open");
            overlay.classList.remove("active");
        }

        if (sectionId === "Annunci" && !annunciLoaded) {
            annunciLoaded = true;
            loadOffers();
        }
        if (sectionId === "Candidature" && !candidatureLoaded) {
            candidatureLoaded = true;
            loadApplications();
        }
    }

    navItems.forEach((item) => {
        item.addEventListener("click", (e) => {
            if (item.id === "navLogout") return;
            e.preventDefault();
            const sectionName = item.id.replace("nav", "");
            switchSection(sectionName);
        });
    });

    document.getElementById("profiloButton")?.addEventListener("click", () => {
        switchSection("Profilo");
    });

    hamburger?.addEventListener("click", () => {
        sidebar.classList.toggle("open");
        overlay.classList.toggle("active");
    });

    overlay?.addEventListener("click", () => {
        sidebar.classList.remove("open");
        overlay.classList.remove("active");
    });

    logoutBtn?.addEventListener("click", (e) => {
        e.preventDefault();
        logoutOverlay.classList.add("active");
    });

    logoutCancel?.addEventListener("click", () => {
        logoutOverlay.classList.remove("active");
    });

    logoutConfirm?.addEventListener("click", () => {
        window.location.href = "/auth/logout";
    });

    document.getElementById("btnGoToAnnunci")?.addEventListener("click", () => {
        switchSection("Annunci");
    });

    // ============ ANNUNCI ============

    function requiredSkillTags(offer) {
        const skillTags = offer.required_skills
            .map((s) => `<span class="co-tag">${escapeHtml(s.name)} · ${SKILL_LV_LABEL_MAP[s.livello_min] || s.livello_min}</span>`)
            .join("");
        const softTags = offer.required_soft_skills
            .map((s) => `<span class="co-tag">${escapeHtml(s.label)}</span>`)
            .join("");
        return skillTags + softTags;
    }

    function renderOffers(list) {
        const container = document.getElementById("annunciList");
        const empty = document.getElementById("annunciEmpty");
        const badge = document.getElementById("badgeAnnunci");

        offers = Array.isArray(list) ? list : [];
        badge.textContent = offers.length;

        if (offers.length === 0) {
            container.style.display = "none";
            empty.style.display = "flex";
            return;
        }

        empty.style.display = "none";
        container.style.display = "grid";
        container.innerHTML = offers
            .map((o) => `
                <div class="offer-card">
                    <div class="offer-card-head">
                        <div>
                            <div class="offer-card-title">${escapeHtml(o.title)}</div>
                            <div class="offer-card-meta">${o.applications_count} candidatura/e · pubblicato il ${formatDate(o.created_at)}</div>
                        </div>
                        <span class="pro-badge ${o.attivo ? "blue" : "gray"}">${o.attivo ? "Attivo" : "Chiuso"}</span>
                    </div>
                    ${o.description ? `<div class="offer-card-desc">${escapeHtml(o.description)}</div>` : ""}
                    <div class="offer-card-tags">${requiredSkillTags(o)}</div>
                    <div class="offer-card-footer">
                        <button class="imp-btn-sm" data-action="edit-offer" data-id="${o.id}">Modifica</button>
                        ${o.attivo ? `<button class="imp-btn-sm danger" data-action="close-offer" data-id="${o.id}">Chiudi annuncio</button>` : ""}
                    </div>
                </div>
            `)
            .join("");
    }

    async function loadOffers({ silent } = {}) {
        if (!silent) {
            document.getElementById("annunciLoading").style.display = "flex";
            document.getElementById("annunciList").style.display = "none";
        }

        try {
            const res = await fetch("/api/company/offers");
            if (!res.ok) throw new Error(`http ${res.status}`);
            renderOffers(await res.json());
        } catch (err) {
            console.error("Errore caricamento annunci:", err);
            if (!silent) showToast("Errore nel caricamento degli annunci");
        } finally {
            document.getElementById("annunciLoading").style.display = "none";
        }
    }

    function renderOfferSkillsEditor() {
        const el = document.getElementById("offerSkillsEditor");
        el.innerHTML = offerSkills
            .map((s, i) => `
                <div class="pro-skill-edit-row">
                    <input type="text" value="${escapeHtml(s.name)}" placeholder="Es. Python" data-skill-index="${i}" data-skill-field="name"/>
                    <select data-skill-index="${i}" data-skill-field="livello">
                        ${["Base", "Intermedio", "Avanzato"]
                        .map((lv) => `<option value="${lv}"${s.livello === lv ? " selected" : ""}>${lv}</option>`)
                        .join("")}
                    </select>
                    <button class="pro-del-btn" data-skill-remove="${i}">✕</button>
                </div>
            `)
            .join("");
    }

    function renderOfferSoftEditor() {
        const el = document.getElementById("offerSoftEditor");
        el.innerHTML = ALL_SOFT_SKILLS.map((s) => {
            const sel = offerSoftSkills.some((soft) => soft.label === s.label);
            return `
                <div class="pro-soft-check${sel ? " selected" : ""}" data-toggle-soft="${escapeHtml(s.label)}" data-icon="${s.icon}">
                    <input type="checkbox"${sel ? " checked" : ""}/>
                    <span class="pro-soft-check-icon">${svgIcon(s.icon)}</span>
                    <span class="pro-soft-check-label">${s.label}</span>
                </div>`;
        }).join("");
    }

    function openOfferModal(offer) {
        editingOfferId = offer ? offer.id : null;
        document.getElementById("offerModalTitle").textContent = offer ? "Modifica annuncio" : "Nuovo annuncio";
        document.getElementById("offerTitle").value = offer ? offer.title : "";
        document.getElementById("offerDescription").value = offer ? (offer.description || "") : "";

        offerSkills = offer
            ? offer.required_skills.map((s) => ({ name: s.name, livello: SKILL_LV_LABEL_MAP[s.livello_min] || "Base" }))
            : [];
        offerSoftSkills = offer
            ? offer.required_soft_skills.map((s) => ({ label: s.label, icon: s.icon }))
            : [];

        renderOfferSkillsEditor();
        renderOfferSoftEditor();
        document.getElementById("offerApiStatus").textContent = "";
        document.getElementById("offerOverlay").classList.add("active");
    }

    function closeOfferModal() {
        document.getElementById("offerOverlay").classList.remove("active");
    }

    async function saveOfferta() {
        const payload = {
            title: document.getElementById("offerTitle").value.trim(),
            description: document.getElementById("offerDescription").value.trim(),
            required_skills: offerSkills
                .filter((s) => String(s.name || "").trim())
                .map((s) => ({ name: s.name.trim(), livello_min: SKILL_LV_DB_MAP[s.livello] || 1 })),
            required_soft_skills: offerSoftSkills.map((s) => ({ label: s.label, icon: s.icon || "i-brain" })),
        };

        if (!payload.title) {
            document.getElementById("offerApiStatus").textContent = "Il titolo è obbligatorio";
            document.getElementById("offerApiStatus").className = "pro-api-status show err";
            return;
        }

        const url = editingOfferId ? `/api/company/offers/${editingOfferId}/update` : "/api/company/offers";
        const btn = document.getElementById("btnSalvaOfferta");
        btn.disabled = true;

        try {
            const res = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            if (!res.ok) throw new Error(`http ${res.status}`);

            closeOfferModal();
            showToast(editingOfferId ? "Annuncio aggiornato" : "Annuncio creato");
            annunciLoaded = false;
            switchSection("Annunci");
        } catch (err) {
            console.error("Errore salvataggio annuncio:", err);
            document.getElementById("offerApiStatus").textContent = "Errore nel salvataggio. Riprova.";
            document.getElementById("offerApiStatus").className = "pro-api-status show err";
        } finally {
            btn.disabled = false;
        }
    }

    async function closeOfferAnnuncio(id) {
        try {
            const res = await fetch(`/api/company/offers/${id}/close`, { method: "POST" });
            if (!res.ok) throw new Error(`http ${res.status}`);
            showToast("Annuncio chiuso");
            annunciLoaded = false;
            switchSection("Annunci");
        } catch (err) {
            console.error("Errore chiusura annuncio:", err);
            showToast("Errore durante la chiusura dell'annuncio");
        }
    }

    document.getElementById("btnNewOffer")?.addEventListener("click", () => openOfferModal(null));
    document.getElementById("offerModalClose")?.addEventListener("click", closeOfferModal);
    document.getElementById("offerModalCancel")?.addEventListener("click", closeOfferModal);
    document.getElementById("offerOverlay")?.addEventListener("click", (e) => {
        if (e.target === document.getElementById("offerOverlay")) closeOfferModal();
    });
    document.getElementById("btnSalvaOfferta")?.addEventListener("click", saveOfferta);
    document.getElementById("offerAddSkillBtn")?.addEventListener("click", () => {
        offerSkills.push({ name: "", livello: "Base" });
        renderOfferSkillsEditor();
    });
    document.getElementById("offerSkillsEditor")?.addEventListener("change", (e) => {
        const { skillIndex, skillField } = e.target.dataset;
        if (skillIndex === undefined || !skillField) return;
        offerSkills[Number(skillIndex)][skillField] = e.target.value;
    });
    document.getElementById("offerSkillsEditor")?.addEventListener("click", (e) => {
        const removeButton = e.target.closest("[data-skill-remove]");
        if (!removeButton) return;
        offerSkills.splice(Number(removeButton.dataset.skillRemove), 1);
        renderOfferSkillsEditor();
    });
    document.getElementById("offerSoftEditor")?.addEventListener("click", (e) => {
        const item = e.target.closest("[data-toggle-soft]");
        if (!item) return;
        const label = item.dataset.toggleSoft;
        const idx = offerSoftSkills.findIndex((s) => s.label === label);
        if (idx === -1) {
            offerSoftSkills.push({ label, icon: item.dataset.icon });
        } else {
            offerSoftSkills.splice(idx, 1);
        }
        renderOfferSoftEditor();
    });

    document.getElementById("annunciList")?.addEventListener("click", (e) => {
        const editBtn = e.target.closest('[data-action="edit-offer"]');
        if (editBtn) {
            const offer = offers.find((o) => String(o.id) === String(editBtn.dataset.id));
            if (offer) openOfferModal(offer);
            return;
        }
        const closeBtn = e.target.closest('[data-action="close-offer"]');
        if (closeBtn) openCloseOfferConfirm(closeBtn.dataset.id);
    });

    let pendingCloseOfferId = null;
    const closeOfferOverlay = document.getElementById("closeOfferOverlay");

    function openCloseOfferConfirm(id) {
        pendingCloseOfferId = id;
        closeOfferOverlay?.classList.add("active");
    }

    function closeCloseOfferConfirm() {
        pendingCloseOfferId = null;
        closeOfferOverlay?.classList.remove("active");
    }

    document.getElementById("closeOfferCancel")?.addEventListener("click", closeCloseOfferConfirm);
    document.getElementById("closeOfferConfirm")?.addEventListener("click", () => {
        const id = pendingCloseOfferId;
        closeCloseOfferConfirm();
        if (id) closeOfferAnnuncio(id);
    });
    closeOfferOverlay?.addEventListener("click", (e) => {
        if (e.target === closeOfferOverlay) closeCloseOfferConfirm();
    });

    // ============ CANDIDATURE ============

    function applicationCard(a) {
        const st = a.student;
        const canAct = a.status === "inviata" || a.status === "vista";

        return `
            <div class="st-card" data-id="${a.id}">
                <div class="st-header">
                    <div class="st-avatar">${initials(st.name, st.surname)}</div>
                    <div class="st-info">
                        <div class="st-name">${escapeHtml(st.name)} ${escapeHtml(st.surname)}</div>
                        <div class="st-school">Candidato per: ${escapeHtml(a.job_offer_title)} · ${formatDate(a.created_at)}</div>
                    </div>
                    <span class="pro-badge ${APP_STATUS_BADGE[a.status] || "gray"}">${APP_STATUS_LABEL[a.status] || a.status}</span>
                </div>
                ${a.message ? `<div class="app-message">${escapeHtml(a.message)}</div>` : ""}
                <div class="st-footer">
                    <button class="st-contact-btn" data-action="contact" data-email="${escapeHtml(st.email)}">Contatta</button>
                    ${canAct ? `
                        <button class="imp-btn-sm" data-action="accept-app" data-id="${a.id}">Accetta</button>
                        <button class="imp-btn-sm danger" data-action="reject-app" data-id="${a.id}">Rifiuta</button>
                    ` : ""}
                </div>
            </div>
        `;
    }

    function renderApplications(list) {
        const container = document.getElementById("candidatureList");
        const empty = document.getElementById("candidatureEmpty");
        const badge = document.getElementById("badgeCandidature");

        applications = Array.isArray(list) ? list : [];
        badge.textContent = applications.length;

        if (applications.length === 0) {
            container.style.display = "none";
            empty.style.display = "flex";
            return;
        }

        empty.style.display = "none";
        container.style.display = "grid";
        container.innerHTML = applications.map(applicationCard).join("");
    }

    function renderRecentApplications() {
        const list = document.getElementById("recentApplicationsList");
        if (!list) return;

        if (!applications || applications.length === 0) {
            list.innerHTML = `<div class="section-state"><span>Nessuna candidatura recente</span></div>`;
            return;
        }

        list.innerHTML = applications
            .slice(0, 3)
            .map((a) => `
                <div class="route-item">
                    <div class="route-icon">${svgIcon("i-users")}</div>
                    <div class="route-info">
                        <div class="route-from-to">${escapeHtml(a.student.name)} ${escapeHtml(a.student.surname)} → ${escapeHtml(a.job_offer_title)}</div>
                        <div class="route-meta">${formatDate(a.created_at)}</div>
                    </div>
                    <span class="pro-badge ${APP_STATUS_BADGE[a.status] || "gray"}">${APP_STATUS_LABEL[a.status] || a.status}</span>
                </div>
            `)
            .join("");
    }

    async function loadApplications({ silent } = {}) {
        if (!silent) {
            document.getElementById("candidatureLoading").style.display = "flex";
            document.getElementById("candidatureList").style.display = "none";
        }

        try {
            const res = await fetch("/api/company/applications");
            if (!res.ok) throw new Error(`http ${res.status}`);
            const data = await res.json();
            renderApplications(data);
            renderRecentApplications();
        } catch (err) {
            console.error("Errore caricamento candidature:", err);
            if (!silent) showToast("Errore nel caricamento delle candidature");
        } finally {
            document.getElementById("candidatureLoading").style.display = "none";
        }
    }

    async function setApplicationStatus(id, status) {
        try {
            const res = await fetch(`/api/company/applications/${id}/status`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status }),
            });
            if (!res.ok) throw new Error(`http ${res.status}`);
            showToast(status === "accettata" ? "Candidatura accettata" : "Candidatura rifiutata");
            candidatureLoaded = false;
            loadApplications();
        } catch (err) {
            console.error("Errore aggiornamento candidatura:", err);
            showToast("Errore durante l'aggiornamento della candidatura");
        }
    }

    document.getElementById("candidatureList")?.addEventListener("click", (e) => {
        const contactBtn = e.target.closest('[data-action="contact"]');
        if (contactBtn) {
            window.location.href = `mailto:${contactBtn.dataset.email}`;
            return;
        }
        const acceptBtn = e.target.closest('[data-action="accept-app"]');
        if (acceptBtn) {
            setApplicationStatus(acceptBtn.dataset.id, "accettata");
            return;
        }
        const rejectBtn = e.target.closest('[data-action="reject-app"]');
        if (rejectBtn) setApplicationStatus(rejectBtn.dataset.id, "rifiutata");
    });

    // Precarica le candidature per la card "Candidature Recenti" della dashboard.
    loadApplications({ silent: true }).then(() => {
        candidatureLoaded = true;
    });

    // Precarica gli annunci per aggiornare subito il numerino nella sidebar.
    loadOffers({ silent: true }).then(() => {
        annunciLoaded = true;
    });

    // ============ PROFILO AZIENDALE ============

    function textOrEmpty(id) {
        const value = document.getElementById(id)?.textContent?.trim();
        return value && value !== "--" ? value : "";
    }

    function openCompanyProfileModal() {
        document.getElementById("fSettore").value = textOrEmpty("proValSettore");
        document.getElementById("fTelefonoAzienda").value = textOrEmpty("proValTelefono");
        document.getElementById("fSitoWeb").value = textOrEmpty("proValSito");
        document.getElementById("fDescrizione").value = textOrEmpty("proValDescrizione");
        document.getElementById("companyProfileApiStatus").textContent = "";
        document.getElementById("companyProfileOverlay").classList.add("active");
    }

    function closeCompanyProfileModal() {
        document.getElementById("companyProfileOverlay").classList.remove("active");
    }

    async function saveCompanyProfilo() {
        const payload = {
            settore: document.getElementById("fSettore").value.trim(),
            telefono: document.getElementById("fTelefonoAzienda").value.trim(),
            sito_web: document.getElementById("fSitoWeb").value.trim(),
            descrizione: document.getElementById("fDescrizione").value.trim(),
        };

        const btn = document.getElementById("btnSalvaProfiloAzienda");
        btn.disabled = true;

        try {
            const res = await fetch("/api/company/profile/save", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            if (!res.ok) throw new Error(`http ${res.status}`);

            document.getElementById("proValSettore").textContent = payload.settore || "--";
            document.getElementById("proValTelefono").textContent = payload.telefono || "--";
            document.getElementById("proValSito").textContent = payload.sito_web || "--";
            document.getElementById("proValDescrizione").textContent = payload.descrizione || "--";

            closeCompanyProfileModal();
            showToast("Profilo aziendale aggiornato");
        } catch (err) {
            console.error("Errore salvataggio profilo azienda:", err);
            document.getElementById("companyProfileApiStatus").textContent = "Errore nel salvataggio. Riprova.";
            document.getElementById("companyProfileApiStatus").className = "pro-api-status show err";
        } finally {
            btn.disabled = false;
        }
    }

    document.getElementById("btnEditProfilo")?.addEventListener("click", openCompanyProfileModal);
    document.getElementById("companyProfileModalClose")?.addEventListener("click", closeCompanyProfileModal);
    document.getElementById("companyProfileModalCancel")?.addEventListener("click", closeCompanyProfileModal);
    document.getElementById("companyProfileOverlay")?.addEventListener("click", (e) => {
        if (e.target === document.getElementById("companyProfileOverlay")) closeCompanyProfileModal();
    });
    document.getElementById("btnSalvaProfiloAzienda")?.addEventListener("click", saveCompanyProfilo);

    // ============ NOTIFICHE ============

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
        return date.toLocaleString("it-IT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
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
                    ${!n.is_read ? `<div class="notif-item-footer">
                        <button class="notif-item-check" type="button" title="Segna come letta" data-notif-check="${n.id}">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 4 4 10-10"/></svg>
                        </button>
                    </div>` : ""}
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
        document.getElementById("notifDetailsOverlay")?.classList.remove("active");
    }

    async function markNotificationRead(id) {
        const notif = notifications.find((n) => n.id === id);
        if (!notif || notif.is_read) return;

        notif.is_read = true;
        renderNotifications();

        try {
            await fetch("/api/company/notifications/read", {
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

    document.getElementById("notificationsToggle")?.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleNotifPanel();
    });

    document.getElementById("notifList")?.addEventListener("click", (e) => {
        const checkBtn = e.target.closest("[data-notif-check]");
        if (checkBtn) {
            e.stopPropagation();
            markNotificationRead(Number(checkBtn.dataset.notifCheck));
            return;
        }
        const item = e.target.closest(".notif-item");
        if (item) openNotifDetails(Number(item.dataset.notifId));
    });

    document.getElementById("notifDetailsClose")?.addEventListener("click", closeNotifDetails);
    document.getElementById("notifDetailsOverlay")?.addEventListener("click", (e) => {
        if (e.target === document.getElementById("notifDetailsOverlay")) closeNotifDetails();
    });

    document.addEventListener("click", (e) => {
        const wrap = document.getElementById("notifWrap");
        if (wrap && !wrap.contains(e.target)) closeNotifPanel();
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            sidebar.classList.remove("open");
            overlay.classList.remove("active");
            logoutOverlay.classList.remove("active");
            closeOfferModal();
            closeCloseOfferConfirm();
            closeCompanyProfileModal();
            closeNotifDetails();
            closeNotifPanel();
        }
    });

    loadNotificationsData();
    renderNotifications();
});
