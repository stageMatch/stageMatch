# design-system.md

## Palette Colori (StageMatch)

L'identità visiva si basa su un contrasto tra l'eleganza del **Blu Notte** e l'energia del **Verde Smeraldo**.

### Colori Core
- **Midnight Blue (Background):** `#0A0E1A` - Usato per lo sfondo principale.
- **Midnight Blue Lighter (Panels):** `#111625` - Usato per card, sidebar e pannelli sovrapposti.
- **Emerald Green (Primary Accent):** `#2ECC71` - Usato per pulsanti primary, icone di successo, e bordi attivi.
- **Emerald Green Dark:** `#27AE60` - Per hover sui pulsanti.
- **Text Primary:** `#E8E6F4` - Bianco sporco per massima leggibilità su fondo scuro.
- **Text Muted:** `#7B74A0` - Per descrizioni e testi secondari.

### Spaziatura e Bordi
- **Bordi (`--border`):** grigio moderno traslucido, non verde — `rgba(255, 255, 255, 0.1)` su tema scuro, `rgba(15, 23, 42, 0.13)` su tema chiaro. Un bordo verde trasparente su pannello scuro rende visivamente "nero-verde" sporco invece che un accento pulito; il grigio neutro è più leggibile e più moderno su entrambi i temi.
- **Bordi con accento (`--border-acc`):** restano verde smeraldo pieno (`var(--emerald-green)`), riservati a stati attivi/selezionati/hover intenzionali (nav item attivo, tab selezionata, "best match", pill di trasporto attiva) — mai come bordo di default di card/pannelli.
- **Radius:** `12px` per card e pannelli, `8px` per pulsanti e input.

## Tema chiaro

Alcune pagine supportano anche un tema chiaro, attivato con l'attributo `data-theme="light"` sull'elemento `<html>` (vedi `resources/js/theme.js`). Il tema chiaro **inverte solo le variabili funzionali** (sfondo, pannelli, testo), non le costanti di brand:

- **Midnight Blue / Emerald Green:** invariati in entrambi i temi — restano le costanti di brand, mai ridefinite dentro `[data-theme="light"]` (servono ancora, ad es., per il testo scuro su bottoni verdi).
- **Sfondo (`--bg`):** `#F7F9FC` (quasi bianco) invece di Midnight Blue.
- **Pannelli (`--panel`):** `#FFFFFF` invece di Midnight Blue Lighter.
- **Testo primario (`--text`):** riusa il valore di Midnight Blue (`#0A0E1A`) come colore testo.
- **Testo secondario (`--text-muted`):** `#5B6478`.
- **Bordi (`--border`):** `rgba(10, 14, 26, 0.1)` invece del verde trasparente.
- **Accento (`--emerald-green`):** invariato — resta il verde del brand in entrambi i temi, usato per sfondi pieni (bottoni, badge, icone) dove il testo sopra è scuro (`var(--midnight-blue)`).
- **Testo verde (`--green-text`):** l'Emerald Green `#2ECC71` usato come *colore del testo* su sfondo chiaro (`--panel: #FFFFFF`, `--bg: #F7F9FC`) ha un contrasto insufficiente (~1.9:1) ed è poco leggibile. Per questo `--green-text` è una variabile funzionale separata da `--emerald-green`: resta identica a `--emerald-green` in tema scuro, ma diventa una tonalità più scura (`#1B8A4C`, contrasto ~5:1 su bianco) in tema chiaro. Ogni `color:` che prima puntava a `var(--emerald-green)`/`var(--green)` va convertito a `var(--green-text)`; gli usi come `background`, `border-color` o `box-shadow` restano invariati su `var(--emerald-green)`.

Vedi `assets/brand-variables.css` per il blocco `:root[data-theme="light"]` completo, da replicare (con lo stesso criterio: solo variabili funzionali, mai le costanti di brand) in ogni CSS di pagina che duplica le proprie variabili.

### Regola obbligatoria: mai colori letterali per testo/superfici

Il tema chiaro si rompe quasi sempre non nel blocco `[data-theme="light"]` stesso, ma nel resto del file: se il CSS usa colori letterali pensati "a occhio" per lo sfondo scuro, quei valori restano fissi quando le variabili si invertono, causando testo bianco su pannello bianco o overlay chiari invisibili.

**Vietato** in qualsiasi CSS di pagina (fuori dal blocco `:root`/`:root[data-theme="light"]`):
- `color: white`, `color: #fff`/`#ffffff`, o `rgba(255, 255, 255, X)` per testo — usare sempre `var(--text)` o `var(--text-muted)` (l'opacità va simulata con una variabile muted dedicata, non con un `white` trasparente).
- `background: rgba(255, 255, 255, X)` come "velo chiaro su sfondo scuro" per superfici/hover/bordi — usare `var(--surface)`, `var(--surface-hov)` o `var(--border)`, che nel file `dashboard-student.css` sono già definite per invertirsi correttamente (`rgba(255,255,255,.03)` in dark → `rgba(10,14,26,.03)` in light).
- Colori esadecimali scuri fissi per superfici che dovrebbero seguire il tema (es. `background: #1a1830` per un pannello/dropdown) — vanno legati a `var(--panel)` o a una nuova variabile funzionale, non lasciati fissi.
- `color: var(--emerald-green)` / `color: var(--green)` per testo — usare `var(--green-text)`, che in tema chiaro scurisce automaticamente il verde per restare leggibile (vedi "Testo verde" sopra).
- `border: 1px solid var(--border)`/`border-color` con un colore verde trasparente scritto a mano (es. `rgba(46, 204, 113, 0.12)`) al posto della variabile `--border` — il bordo di default di card/pannelli deve sempre passare da `var(--border)` (grigio neutro), mai da un verde trasparente scritto inline.

Fanno eccezione solo gli elementi che devono restare scuri/chiari a prescindere dal tema per motivi di contrasto fisso (es. testo scuro su bottone verde smeraldo, che usa `var(--midnight-blue)` — quello è corretto perché è una costante di brand, non un colore "a occhio").

**Checklist prima di considerare completo un lavoro sul tema chiaro:**
1. `grep -n "white\|rgba(255, *255, *255" nomefile.css` sul file toccato: ogni risultato fuori dal blocco `:root` va giustificato o sostituito con una variabile.
2. `grep -n "color: var(--emerald-green)\|color: var(--green)" nomefile.css`: ogni risultato va convertito in `var(--green-text)`.
3. `grep -n "rgba(46, 204, 113" nomefile.css` sulle righe `border:`/`border-color:` di card/pannelli generici (non stati attivi/hover intenzionali): vanno convertite a `var(--border)`.
4. Attivare `data-theme="light"` (via `theme.js`/devtools) e controllare a occhio ogni sezione della pagina, non solo quella modificata — un colore letterale in una sezione lontana da quella toccata è la causa più comune di regressioni.

## Pattern UI

### Pulsanti
```css
.btn-primary {
    background: var(--emerald-green);
    color: #0A0E1A;
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.3s ease;
}
.btn-primary:hover {
    background: var(--emerald-green-dark);
    transform: translateY(-1px);
}
```

### Card / Pannelli
```css
.card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
}
```
