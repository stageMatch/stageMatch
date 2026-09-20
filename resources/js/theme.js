/*
 * Script condiviso da tutte le pagine (unica eccezione alla convenzione
 * "un JS per pagina" del progetto): applica il tema chiaro/scuro il prima
 * possibile, prima del paint, per evitare un flash del tema sbagliato.
 *
 * Sorgente della preferenza:
 * - se la pagina è renderizzata per un utente loggato con un record DB
 *   reale, un tag <meta name="app-theme" content="dark|light" data-role="user|company">
 *   viene emesso lato server; se il valore salvato in localStorage differisce
 *   (es. l'utente ha cambiato tema su una pagina pubblica mentre la sessione
 *   era ancora valida), vince localStorage e viene sincronizzato sul DB;
 * - altrimenti si usa l'ultimo valore noto in localStorage, con fallback
 *   alla preferenza del sistema operativo (prefers-color-scheme).
 */
(function () {
    var STORAGE_KEY = "stagematch-theme";
    var meta = document.querySelector('meta[name="app-theme"]');
    var theme;

    var stored = null;
    try {
        stored = localStorage.getItem(STORAGE_KEY);
    } catch (e) {
        stored = null;
    }

    if (meta) {
        var dbTheme = meta.content === "light" ? "light" : "dark";

        if ((stored === "light" || stored === "dark") && stored !== dbTheme) {
            theme = stored;

            var role = meta.getAttribute("data-role") === "company" ? "company" : "user";
            var endpoint = role === "company"
                ? "/api/companies/preferences/save"
                : "/api/users/preferences/save";

            fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ color_mode: theme })
            }).catch(function () {
                // sync non riuscita: il tema resta comunque applicato lato client.
            });
        } else {
            theme = dbTheme;
        }
    } else if (stored === "light" || stored === "dark") {
        theme = stored;
    } else {
        var prefersLight = false;
        try {
            prefersLight = window.matchMedia("(prefers-color-scheme: light)").matches;
        } catch (e) {
            prefersLight = false;
        }
        theme = prefersLight ? "light" : "dark";
    }

    document.documentElement.setAttribute("data-theme", theme);
    try {
        localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
        // localStorage non disponibile: il tema corrente resta comunque applicato.
    }

    window.__setTheme = function (value) {
        var next = value === "light" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        try {
            localStorage.setItem(STORAGE_KEY, next);
        } catch (e) {
            // ignorato: la preferenza resta comunque applicata per la sessione corrente.
        }
    };
})();
