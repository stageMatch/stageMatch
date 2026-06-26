document.addEventListener("DOMContentLoaded", () => {
    const sliderContainer = document.getElementById("sliderContainer");
    const switchLinks = document.querySelectorAll(".switch-link");
    const registerForm = document.getElementById("registerForm");

    // Sincronizza altezza slider con il pannello attivo
    function syncSliderHeight() {
        const activePanel = sliderContainer.querySelector(".auth-panel.active") || sliderContainer.querySelector(".auth-panel");
        if (activePanel) {
            sliderContainer.style.height = activePanel.offsetHeight + "px";
        }
    }

    // Init: altezza iniziale
    setTimeout(syncSliderHeight, 100);

    // Ricalcola altezza al ridimensionamento della finestra
    window.addEventListener("resize", syncSliderHeight);

    // Switch tra Login e Registrazione
    switchLinks.forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const target = link.getAttribute("data-target");
            const loginPanel = document.getElementById("loginPanel");
            const registerPanel = document.getElementById("registerPanel");

            if (target === "register") {
                loginPanel.classList.remove("active");
                registerPanel.classList.add("active");
                sliderContainer.classList.add("show-register");
                
                // Sincronizza altezza immediatamente
                syncSliderHeight();
                
                setTimeout(() => {
                    document.getElementById("register-name")?.focus({ preventScroll: true });
                }, 400);
            } else {
                registerPanel.classList.remove("active");
                loginPanel.classList.add("active");
                sliderContainer.classList.remove("show-register");
                
                if (registerForm) registerForm.reset();
                
                // Sincronizza altezza immediatamente
                syncSliderHeight();
                
                setTimeout(() => {
                    document.getElementById("loginGoogleBtn")?.focus({ preventScroll: true });
                }, 400);
            }
        });
    });

    // Handle Login con Google
    const loginGoogleBtn = document.getElementById("loginGoogleBtn");
    if (loginGoogleBtn) {
        loginGoogleBtn.addEventListener("click", () => {
            loginGoogleBtn.disabled = true;
            loginGoogleBtn.innerHTML = "Caricamento...";
            window.location.href = '/auth/company/login';
        });
    }

    // Handle Register form submission
    if (registerForm) {
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const submitBtn = registerForm.querySelector('button[type="submit"]');
            const originalBtnContent = submitBtn.innerHTML;

            const name = document.getElementById("register-name").value.trim();
            const access_code = document.getElementById("register-access-code").value.trim();
            const via = document.getElementById("register-via").value.trim();
            const civico = document.getElementById("register-civico").value.trim();
            const cap = document.getElementById("register-cap").value.trim();
            const citta = document.getElementById("register-citta").value.trim();
            const acceptTerms = document.getElementById("accept-terms").checked;

            if (!acceptTerms) {
                showNotification("Devi accettare i Termini e Condizioni", "warning");
                return;
            }

            // UI State
            submitBtn.disabled = true;
            submitBtn.innerHTML = "Registrazione in corso...";

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
                    }, 1200);
                } else {
                    const data = await response.json();
                    showNotification(data.error || 'Errore durante la registrazione', "error");
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnContent;
                }
            } catch (error) {
                console.error('Registration error:', error);
                showNotification('Errore di connessione. Riprova più tardi.', "error");
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnContent;
            }
        });
    }

    // Funzione per mostrare notifiche (Toast) migliorata
    function showNotification(message, type = "info", duration = 4000) {
        let toastContainer = document.querySelector(".toast-container");
        if (!toastContainer) {
            toastContainer = document.createElement("div");
            toastContainer.className = "toast-container";
            document.body.appendChild(toastContainer);
        }

        const toast = document.createElement("div");
        toast.className = `custom-toast ${type}`;
        
        const titles = { success: "Successo", error: "Errore", warning: "Attenzione", info: "Info" };

        const icons = {
            success: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`,
            error: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`,
            warning: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`,
            info: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`
        };

        toast.innerHTML = `
            <div class="toast-icon">${icons[type] || icons.info}</div>
            <div class="toast-content">
                <div class="toast-title">${titles[type] || titles.info}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" aria-label="Chiudi">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
        `;

        toastContainer.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add("show"));

        let autoDismissTimer = setTimeout(() => dismissToast(), duration);

        function dismissToast() {
            toast.classList.remove("show");
            setTimeout(() => {
                toast.remove();
                if (toastContainer.childNodes.length === 0) toastContainer.remove();
            }, 500);
        }

        toast.querySelector(".toast-close").addEventListener("click", (e) => {
            e.stopPropagation();
            clearTimeout(autoDismissTimer);
            dismissToast();
        });
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
        if (!query || query.length < 2) return [];
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
        let currentResults = [];

        function renderList(results) {
            currentResults = results;
            list.innerHTML = "";
            activeIdx = -1;

            if (!results.length) {
                list.classList.remove("open");
                return;
            }

            const q = input.value.trim();
            results.forEach((c, i) => {
                const li = document.createElement("li");
                const n = c.nome;
                const matchIdx = n.toLowerCase().indexOf(q.toLowerCase());
                
                if (matchIdx >= 0) {
                    const before = n.substring(0, matchIdx);
                    const match = n.substring(matchIdx, matchIdx + q.length);
                    const after = n.substring(matchIdx + q.length);
                    li.innerHTML = `${before}<em>${match}</em>${after}` +
                        (c.provincia ? ` <span class="prov-tag">(${c.provincia})</span>` : "");
                } else {
                    li.textContent = c.nome + (c.provincia ? ` (${c.provincia})` : "");
                }

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
            currentResults = [];
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

            if (e.key === "ArrowDown") {
                if (!list.classList.contains("open")) {
                    renderList(searchComuni(input.value));
                    return;
                }
                e.preventDefault();
                activeIdx = Math.min(activeIdx + 1, items.length - 1);
                highlightItem(activeIdx);
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                activeIdx = Math.max(activeIdx - 1, 0);
                highlightItem(activeIdx);
            } else if (e.key === "Enter") {
                if (list.classList.contains("open") && activeIdx >= 0) {
                    e.preventDefault();
                    if (currentResults[activeIdx]) selectItem(currentResults[activeIdx]);
                }
            } else if (e.key === "Escape" || e.key === "Tab") {
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
