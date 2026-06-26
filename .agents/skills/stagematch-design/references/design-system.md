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
- **Bordi:** `1px solid rgba(46, 204, 113, 0.1)` (Verde trasparente per un effetto glow soffuso).
- **Radius:** `12px` per card e pannelli, `8px` per pulsanti e input.

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
