"use strict";

const overlay = document.getElementById("modalOverlay");
const openBtn = document.getElementById("openModal");
const closeBtn = document.getElementById("closeModal");
const cancelBtn = document.getElementById("cancelBtn");
const form = document.getElementById("studentForm");
const successMsg = document.getElementById("successMsg");
const modalFooter = document.getElementById("modalFooter");
const submitBtn = document.getElementById("submitBtn");
const submitLabel = document.getElementById("submitLabel");
const progressFill = document.getElementById("progressFill");

const fields = {
    nome: document.getElementById("nome"),
    cognome: document.getElementById("cognome"),
    email: document.getElementById("email"),
    data_nascita: document.getElementById("data_nascita"),
    sesso: document.getElementById("sesso"),
    comune_nascita: document.getElementById("comune_nascita"),
    comune_nascita_code: document.getElementById("comune_nascita_code"),
    codice_fiscale: document.getElementById("codice_fiscale"),
    telefono: document.getElementById("telefono"),
    indirizzo_studio: document.getElementById("indirizzo_studio"),
    classe: document.getElementById("classe"),
    classe_custom: document.getElementById("classe_custom"),
    via: document.getElementById("via"),
    civico: document.getElementById("civico"),
    cap: document.getElementById("cap"),
    citta_residenza: document.getElementById("citta_residenza"),
    privacy_ack: document.getElementById("privacy_ack"),
};

const STUDY_CLASS_CODES = {
    "Informatica e Telecomunicazioni": "I",
    "Meccanica, Meccatronica ed Energia": "M",
    "Elettronica, Elettrotecnica ed Automazione": "E",
    "Sistema Moda Tessile": "T",
};
const CLASS_YEARS = ["1", "2", "3", "4", "5"];
const CLASS_SECTIONS = ["A", "B", "C", "D", "E", "F", "G"];
const CUSTOM_CLASS_VALUE = "__custom__";

let comuniDB = [];

/** ─── Caricamento Comuni ─── */
async function loadComuni() {
    try {
        const res = await fetch("https://raw.githubusercontent.com/axiostudio/comuni-italiani/refs/heads/main/data/import/json/gi_comuni.json");
        if (!res.ok) throw new Error(`[ERROR] ${res.status}`);
        const raw = await res.json();
        comuniDB = raw.map(c => ({
            nome: (c.denominazione_ita || "").trim(),
            codiceBelfiore: (c.codice_belfiore || "").trim().toUpperCase(),
            provincia: (c.sigla_provincia || "").trim().toUpperCase(),
        })).filter(c => c.nome);
    } catch (e) {
        console.error("Errore caricamento comuni:", e);
        comuniDB = [];
    }
}

function normalize(s) {
    return (s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, " ").trim();
}

function searchComuni(query, limit = 8) {
    if (!query) return [];
    const q = normalize(query);
    return comuniDB.filter(c => normalize(c.nome).startsWith(q)).slice(0, limit);
}

function findComuneByName(name) {
    const q = normalize(name);
    return comuniDB.find(c => normalize(c.nome) === q) || null;
}

/** ─── Gestione Classe ─── */
function populateClassSelect(indirizzo) {
    const select = fields.classe;
    const studyCode = STUDY_CLASS_CODES[indirizzo];
    if (!select || !studyCode) return;

    select.innerHTML = '<option value="" disabled selected>Seleziona classe...</option>';
    CLASS_YEARS.forEach(y => {
        CLASS_SECTIONS.forEach(s => {
            const code = `${y}${studyCode}${s}`;
            const opt = document.createElement("option");
            opt.value = code;
            opt.textContent = code;
            select.appendChild(opt);
        });
    });

    const customOpt = document.createElement("option");
    customOpt.value = CUSTOM_CLASS_VALUE;
    customOpt.textContent = "Altro (Specifica...)";
    select.appendChild(customOpt);

    select.disabled = false;
    fields.classe_custom.hidden = true;
}

fields.indirizzo_studio?.addEventListener("change", e => populateClassSelect(e.target.value));
fields.classe?.addEventListener("change", e => {
    const isCustom = e.target.value === CUSTOM_CLASS_VALUE;
    fields.classe_custom.hidden = !isCustom;
    if (isCustom) fields.classe_custom.focus();
});

/** ─── Autocomplete ─── */
function setupAutocomplete(inputId, listId, onSelect) {
    const input = document.getElementById(inputId);
    const list = document.getElementById(listId);

    input.addEventListener("input", () => {
        const results = searchComuni(input.value);
        list.innerHTML = "";
        if (!results.length) {
            list.classList.remove("open");
            return;
        }
        results.forEach((c, i) => {
            const li = document.createElement("li");
            li.textContent = `${c.nome} (${c.provincia})`;
            li.addEventListener("click", () => {
                input.value = c.nome;
                list.classList.remove("open");
                if (onSelect) onSelect(c);
            });
            list.appendChild(li);
        });
        list.classList.add("open");
    });

    document.addEventListener("click", e => {
        if (!input.contains(e.target) && !list.contains(e.target)) list.classList.remove("open");
    });
}

/** ─── Codice Fiscale ─── */
// (Manteniamo la logica di calcolo esistente ma la rendiamo più compatta)
const CF_ODD = { 0:1, 1:0, 2:5, 3:7, 4:9, 5:13, 6:15, 7:17, 8:19, 9:21, A:1, B:0, C:5, D:7, E:9, F:13, G:15, H:17, I:19, J:21, K:2, L:4, M:18, N:20, O:11, P:3, Q:6, R:8, S:12, T:14, U:16, V:10, W:22, X:25, Y:24, Z:23 };
function cfPart(s, isName = false) {
    const chars = s.toUpperCase().replace(/[^A-Z]/g, "");
    const cons = chars.split("").filter(c => !"AEIOU".includes(c));
    const vows = chars.split("").filter(c => "AEIOU".includes(c));
    let res = "";
    if (isName && cons.length >= 4) res = cons[0] + cons[2] + cons[3];
    else res = (cons.join("") + vows.join("") + "XXX").slice(0, 3);
    return res;
}

document.getElementById("cfCalcBtn")?.addEventListener("click", () => {
    const d = fields.data_nascita.value;
    const s = fields.sesso.value;
    const c = fields.comune_nascita_code.value;
    if (!d || !s || !c) {
        alert("Inserisci Data di Nascita, Sesso e Comune di Nascita.");
        return;
    }
    const [y, m, day] = d.split("-").map(Number);
    const partial = cfPart(fields.cognome.value) + cfPart(fields.nome.value, true) +
                  String(y).slice(-2) + "ABCDEHLMPRST"[m-1] +
                  String(s === "F" ? day + 40 : day).padStart(2, "0") + c;

    let sum = 0;
    for (let i = 0; i < 15; i++) {
        const char = partial[i];
        if (i % 2 === 0) sum += CF_ODD[char];
        else sum += isNaN(char) ? char.charCodeAt(0) - 65 : parseInt(char);
    }
    fields.codice_fiscale.value = partial + String.fromCharCode(65 + (sum % 26));
    fields.codice_fiscale.classList.remove("invalid");
});

/** ─── Validazione e Invio ─── */
function validate() {
    let valid = true;
    const err = (id, msg) => {
        const el = document.getElementById(`err-${id}`);
        if (el) el.textContent = msg;
        fields[id]?.classList.toggle("invalid", !!msg);
        if (msg) valid = false;
    };

    ["data_nascita", "sesso", "comune_nascita", "codice_fiscale", "telefono", "indirizzo_studio", "classe", "via", "civico", "cap", "citta_residenza"].forEach(id => {
        if (!fields[id].value.trim()) err(id, "Campo obbligatorio");
        else err(id, "");
    });

    if (fields.classe.value === CUSTOM_CLASS_VALUE) {
        if (!fields.classe_custom.value.trim()) {
            err("classe", "Specifica la tua classe");
            fields.classe_custom.classList.add("invalid");
        } else {
            err("classe", "");
            fields.classe_custom.classList.remove("invalid");
        }
    } else {
        fields.classe_custom.classList.remove("invalid");
    }

    if (!fields.privacy_ack.checked) err("privacy_ack", "Accetta l'informativa");
    else err("privacy_ack", "");

    return valid;
}

form?.addEventListener("submit", async e => {
    e.preventDefault();
    if (!validate()) return;

    submitBtn.disabled = true;
    submitLabel.textContent = "Invio in corso...";

    try {
        const fd = new FormData(form);
        if (fields.classe.value === CUSTOM_CLASS_VALUE) fd.set("classe", fields.classe_custom.value);

        const res = await fetch(form.action, { method: "POST", body: fd });
        if (res.ok) {
            form.classList.add("hidden");
            successMsg.classList.add("visible");
            modalFooter.classList.add("hidden");

            // Inizia il riempimento "organico" dopo che il messaggio è apparso
            setTimeout(() => {
                progressFill.style.width = "100%";
            }, 600);

            setTimeout(() => window.location.href = "/logged/dashboard/student", 3200);
        } else {
            throw new Error("Errore nel salvataggio");
        }
    } catch (e) {
        alert(e.message);
        submitBtn.disabled = false;
        submitLabel.textContent = "Salva e continua";
    }
});

/** ─── Modal Control ─── */
const toggleModal = (v) => {
    overlay.classList.toggle("visible", v);
    document.body.style.overflow = v ? "hidden" : "";
};

openBtn?.addEventListener("click", () => toggleModal(true));
closeBtn?.addEventListener("click", () => toggleModal(false));
cancelBtn?.addEventListener("click", () => toggleModal(false));

document.addEventListener("DOMContentLoaded", async () => {
    await loadComuni();
    setupAutocomplete("comune_nascita", "comune_nascita_list", c => {
        fields.comune_nascita_code.value = c.codiceBelfiore;
    });
    setupAutocomplete("citta_residenza", "citta_residenza_list");
    toggleModal(true);
});
