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
            // TODO: Implementare Google OAuth
            // window.location.href = '/auth/google/login';
            showNotification("Autenticazione Google in sviluppo", "info");
        });
    }

    // Handle Register form submission (raccoglie dati, poi avvia Google OAuth)
    if (registerForm) {
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const name = document.getElementById("register-name").value.trim();
            const accessCode = document.getElementById("register-access-code").value.trim();
            const via = document.getElementById("register-via").value.trim();
            const civico = document.getElementById("register-civico").value.trim();
            const cap = document.getElementById("register-cap").value.trim();
            const citta = document.getElementById("register-citta").value.trim();
            const acceptTerms = document.getElementById("accept-terms").checked;

            if (!acceptTerms) {
                showNotification("Devi accettare i Termini e Condizioni", "error");
                return;
            }

            console.log("Registration attempt:", { name, accessCode, via, civico, cap, citta });

            // TODO: salvare i dati di registrazione in sessione/backend,
            // poi redirezionare a Google OAuth per completare l'accesso.
            // Esempio:
            /*
            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, accessCode, via, civico, cap, citta }),
                });
                const data = await response.json();
                if (response.ok) {
                    window.location.href = '/auth/google/register';
                } else {
                    showNotification(data.message || 'Errore durante la registrazione', "error");
                }
            } catch (error) {
                console.error('Registration error:', error);
                showNotification('Errore di connessione. Riprova più tardi.', "error");
            }
            */

            showNotification("Registrazione completata! Reindirizzamento a Google...", "success");
            setTimeout(() => {
                // window.location.href = '/auth/google/register';
            }, 1500);
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
});