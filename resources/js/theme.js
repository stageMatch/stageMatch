/*
 * Script condiviso da tutte le pagine (unica eccezione alla convenzione
 * "un JS per pagina" del progetto): applica il tema chiaro/scuro il prima
 * possibile, prima del paint, per evitare un flash del tema sbagliato.
 *
 * Sorgente della preferenza:
 * - se la pagina è renderizzata per un utente loggato, un tag
 *   <meta name="app-theme" content="dark|light"> viene emesso lato server
 *   (valore letto da UserPreferences.color_mode) e ha priorità;
 * - altrimenti si usa l'ultimo valore noto in localStorage, con fallback
 *   "dark" (palette di default del sito).
 */
(function () {
    var STORAGE_KEY = "stagematch-theme";
    var meta = document.querySelector('meta[name="app-theme"]');
    var theme;

    if (meta) {
        theme = meta.content === "light" ? "light" : "dark";
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch (e) {
            // localStorage non disponibile: il tema corrente resta comunque applicato.
        }
    } else {
        var stored = null;
        try {
            stored = localStorage.getItem(STORAGE_KEY);
        } catch (e) {
            stored = null;
        }
        theme = stored === "light" ? "light" : "dark";
    }

    document.documentElement.setAttribute("data-theme", theme);

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
