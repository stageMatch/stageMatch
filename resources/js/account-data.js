/*
 * Script condiviso da dashboard studente e azienda (come theme.js): gestisce
 * l'eliminazione dell'account con una modale di conferma accessibile.
 *
 * Il pulsante `[data-account-delete]` deve avere `data-delete-url` (endpoint POST).
 * Il download dei dati è un normale link con `download` (nessuna logica qui).
 */
(function () {
    var trigger = document.querySelector("[data-account-delete]");
    if (!trigger) return;

    var overlay = null;
    var confirmBtn = null;
    var cancelBtn = null;
    var errorEl = null;
    var lastFocused = null;

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text) node.textContent = text;
        return node;
    }

    function build() {
        overlay = el("div", "modal-overlay");
        overlay.id = "deleteAccountOverlay";

        var box = el("div", "modal-box");
        box.setAttribute("role", "alertdialog");
        box.setAttribute("aria-modal", "true");
        box.setAttribute("aria-labelledby", "deleteAccountTitle");
        box.setAttribute("aria-describedby", "deleteAccountDesc");

        var title = el("div", "modal-title", "Eliminare il tuo account?");
        title.id = "deleteAccountTitle";

        var desc = el(
            "div",
            "modal-desc",
            "Verranno eliminati definitivamente il profilo e tutti i dati collegati (candidature, match, notifiche, annunci). L'operazione non si può annullare. Prima di procedere puoi scaricare una copia dei tuoi dati."
        );
        desc.id = "deleteAccountDesc";

        errorEl = el("div", "modal-desc");
        errorEl.setAttribute("role", "alert");
        errorEl.hidden = true;

        var actions = el("div", "modal-actions");
        cancelBtn = el("button", "modal-btn-cancel", "Annulla");
        cancelBtn.type = "button";
        confirmBtn = el("button", "modal-btn-confirm", "Elimina definitivamente");
        confirmBtn.type = "button";
        actions.append(cancelBtn, confirmBtn);

        box.append(title, desc, errorEl, actions);
        overlay.appendChild(box);
        document.body.appendChild(overlay);

        cancelBtn.addEventListener("click", close);
        confirmBtn.addEventListener("click", confirmDelete);
        overlay.addEventListener("click", function (e) {
            if (e.target === overlay) close();
        });
        overlay.addEventListener("keydown", trapFocus);
    }

    function trapFocus(e) {
        if (e.key === "Escape") {
            close();
            return;
        }

        if (e.key !== "Tab") return;

        var focusable = [cancelBtn, confirmBtn].filter(function (b) { return !b.disabled; });
        var first = focusable[0];
        var last = focusable[focusable.length - 1];

        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
        }
    }

    function open() {
        if (!overlay) build();

        lastFocused = document.activeElement;
        errorEl.hidden = true;
        overlay.classList.add("active");
        cancelBtn.focus();
    }

    function close() {
        if (!overlay) return;

        overlay.classList.remove("active");

        if (lastFocused && lastFocused.focus) lastFocused.focus();
    }

    async function confirmDelete() {
        confirmBtn.disabled = true;
        cancelBtn.disabled = true;
        errorEl.hidden = true;

        try {
            var response = await fetch(trigger.dataset.deleteUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ confirm: true })
            });

            if (!response.ok) throw new Error(String(response.status));

            var data = await response.json();
            window.location.href = data.redirect || "/";
        } catch (error) {
            errorEl.textContent = "Eliminazione non riuscita. Riprova più tardi.";
            errorEl.hidden = false;
            confirmBtn.disabled = false;
            cancelBtn.disabled = false;
            cancelBtn.focus();
        }
    }

    trigger.addEventListener("click", open);
})();
