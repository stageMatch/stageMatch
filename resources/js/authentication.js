document.addEventListener("DOMContentLoaded", () => {
    const sliderContainer = document.getElementById("sliderContainer");
    const switchLinks = document.querySelectorAll(".switch-link");
    const registerForm = document.getElementById("registerForm");

    // Sincronizza altezza slider con il pannello attivo
    function syncSliderHeight(panel) {
        sliderContainer.style.height = panel.offsetHeight + "px";
    }

    // Init: altezza del pannello login
    syncSliderHeight(document.getElementById("loginPanel"));

    // Switch tra Login e Registrazione
    switchLinks.forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const target = link.getAttribute("data-target");

            if (target === "register") {
                sliderContainer.classList.add("show-register");
                setTimeout(() => syncSliderHeight(document.getElementById("registerPanel")), 50);
                // Reset eventuali errori di validazione
                document.querySelectorAll(".form-input").forEach(input => {
                    input.setCustomValidity("");
                });
            } else {
                sliderContainer.classList.remove("show-register");
                setTimeout(() => syncSliderHeight(document.getElementById("loginPanel")), 50);
                // Reset del form di registrazione
                if (registerForm) registerForm.reset();
                // Reset eventuali errori di validazione
                document.querySelectorAll(".form-input").forEach(input => {
                    input.setCustomValidity("");
                });
            }
        });
    });

    // Handle Login con Google
    const loginGoogleBtn = document.getElementById("loginGoogleBtn");
    if (loginGoogleBtn) {
        loginGoogleBtn.addEventListener("click", () => {
            console.log("Google login clicked");
            window.location.href = '/auth/company/login';
        });
    }

    // Handle Register form submission (raccoglie dati, poi avvia Google OAuth)
    if (registerForm) {
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const name = document.getElementById("register-name").value.trim();
            const access_code = document.getElementById("register-access-code").value.trim();
            const via = document.getElementById("register-via").value.trim();
            const civico = document.getElementById("register-civico").value.trim();
            const cap = document.getElementById("register-cap").value.trim();
            const citta = document.getElementById("register-citta").value.trim();
            const acceptTerms = document.getElementById("accept-terms").checked;

            if (!acceptTerms) {
                showNotification("Devi accettare i Termini e Condizioni", "error");
                return;
            }

            console.log("Registration attempt:", { name, access_code, via, civico, cap, citta });

            try {
                const response = await fetch('/auth/company/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, access_code, via, civico, cap, citta }),
                });
                
                if (response.ok) {
                    showNotification("Dati salvati! Reindirizzamento a Google...", "success");
                    setTimeout(() => {
                        window.location.href = '/auth/company/login';
                    }, 1000);
                } else {
                    const data = await response.json();
                    showNotification(data.error || 'Errore durante la registrazione', "error");
                }
            } catch (error) {
                console.error('Registration error:', error);
                showNotification('Errore di connessione. Riprova più tardi.', "error");
            }
        });
    }

    // Auto-focus sul primo input quando si cambia pannello
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === "class") {
                const isRegister = sliderContainer.classList.contains("show-register");
                setTimeout(() => {
                    if (isRegister) {
                        document.getElementById("register-name")?.focus();
                    } else {
                        document.getElementById("loginGoogleBtn")?.focus();
                    }
                }, 600);
            }
        });
    });

    observer.observe(sliderContainer, {
        attributes: true,
        attributeFilter: ["class"]
    });

    // Funzione per mostrare notifiche
    function showNotification(message, type) {
        console.log(`[${type.toUpperCase()}] ${message}`);
        // TODO: sostituire con un sistema di toast/notifiche visive
        alert(message);
    }

    /* ════════════════════════════════════
       CITY AUTOCOMPLETE LOGIC
       ════════════════════════════════════ */
    let comuniDB = [];

    async function loadComuni() {
        try {
            const res = await fetch("https://raw.githubusercontent.com/axiostudio/comuni-italiani/refs/heads/main/data/import/json/gi_comuni.json");
            if (!res.ok) throw new Error(`[ERROR] ${res.status}`);
            const raw = await res.json();
            comuniDB = raw
                .map((c) => ({
                    nome: (c.denominazione_ita || "").trim(),
                    provincia: (c.sigla_provincia || "").trim().toUpperCase(),
                }))
                .filter((c) => c.nome);
        } catch (err) {
            console.error("Errore caricamento comuni:", err);
            comuniDB = [];
        }
    }

    function normalizeComuneName(value) {
        return (value || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/\s+/g, " ")
            .trim();
    }

    function searchComuni(query, limit = 8) {
        if (!query) return [];
        const q = normalizeComuneName(query);
        return comuniDB
            .filter((c) => {
                const n = normalizeComuneName(c.nome);
                return n.startsWith(q);
            })
            .slice(0, limit);
    }

    function setupAutocomplete(inputId, listId, { onSelect } = {}) {
        const input = document.getElementById(inputId);
        const list = document.getElementById(listId);
        if (!input || !list) return;

        let activeIdx = -1;

        function renderList(results) {
            list.innerHTML = "";
            activeIdx = -1;
            if (!results.length) {
                list.classList.remove("open");
                return;
            }

            const q = input.value.trim();
            results.forEach((c, i) => {
                const li = document.createElement("li");
                const hl = c.nome.substring(0, q.length);
                const rest = c.nome.substring(q.length);
                li.innerHTML = `<em>${hl}</em>${rest}` + (c.provincia ? ` <span style="opacity:.5; font-size:0.85em; margin-left:4px;">(${c.provincia})</span>` : "");
                li.setAttribute("role", "option");
                li.addEventListener("mousedown", (e) => {
                    e.preventDefault();
                    selectItem(c);
                });
                list.appendChild(li);
            });
            list.classList.add("open");
        }

        function selectItem(comune) {
            input.value = comune.nome;
            list.classList.remove("open");
            list.innerHTML = "";
            if (onSelect) onSelect(comune);
        }

        function highlightItem(idx) {
            const items = list.querySelectorAll("li");
            items.forEach((li, i) => li.classList.toggle("active", i === idx));
            if (idx >= 0 && items[idx]) {
                items[idx].scrollIntoView({ block: "nearest" });
            }
        }

        input.addEventListener("input", () => {
            renderList(searchComuni(input.value));
        });

        input.addEventListener("keydown", (e) => {
            const items = list.querySelectorAll("li");
            if (!items.length) return;

            if (e.key === "ArrowDown") {
                e.preventDefault();
                activeIdx = Math.min(activeIdx + 1, items.length - 1);
                highlightItem(activeIdx);
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                activeIdx = Math.max(activeIdx - 1, 0);
                highlightItem(activeIdx);
            } else if (e.key === "Enter" && activeIdx >= 0) {
                e.preventDefault();
                const results = searchComuni(input.value);
                if (results[activeIdx]) selectItem(results[activeIdx]);
            } else if (e.key === "Escape") {
                list.classList.remove("open");
            }
        });

        document.addEventListener("click", (e) => {
            if (!input.contains(e.target) && !list.contains(e.target)) {
                list.classList.remove("open");
            }
        });
    }

    // Inizializza caricamento e autocomplete
    loadComuni();
    setupAutocomplete("register-citta", "register-citta-list");
});