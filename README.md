# stageMatch

Un'applicazione web full-stack che abbina i profili degli studenti alle aziende per individuare le opportunità di stage più adatte.

## Descrizione

stageMatch nasce per semplificare l'incontro tra studenti e aziende in cerca di tirocinanti: gli studenti costruiscono un profilo con competenze, preferenze e disponibilità, mentre le aziende pubblicano le proprie opportunità, e l'applicazione si occupa di individuare gli abbinamenti più rilevanti.

L'autenticazione avviene tramite Google OAuth, i dati sono gestiti con SQLAlchemy su SQLite e le funzionalità di geocoding, autocompletamento indirizzi e calcolo dei percorsi sono delegate a un servizio proxy interno dedicato, così da valutare anche la vicinanza geografica tra studente e azienda nel processo di abbinamento.

## Funzionalità principali

- **Profili studente**: dati anagrafici, competenze tecniche (skill) e trasversali (soft skill), preferenze e cronologia degli indirizzi/percorsi cercati.
- **Profili azienda**: registrazione tramite Google OAuth e pubblicazione delle informazioni utili all'abbinamento con gli studenti.
- **Autenticazione**: login di studenti e aziende tramite Google OAuth, gestito interamente dall'applicazione.
- **Mappa e calcolo percorsi**: ricerca indirizzi con autocompletamento (Photon), geocoding (Nominatim) e calcolo del tragitto casa-azienda (OpenRouteService), il tutto mediato dal servizio geo-proxy interno.
- **Gestione privacy**: tracciamento del consenso privacy per utente, con versionamento della policy (`PRIVACY_POLICY_VERSION`).
- **Controlli di accesso**: rate limiting delle sessioni simultanee (per singolo utente e a livello globale), persistito su database. Ogni utente può inoltre consultare le proprie sessioni attive e terminarle da Impostazioni.
- **Tema chiaro/scuro**: preferenza persistita per utente (`UserPreferences.color_mode`) e per azienda (`Company.color_mode`), applicata a tutte le pagine tramite `resources/js/theme.js`. Sulle pagine pubbliche (es. la landing) il tema è scelto liberamente e salvato solo in `localStorage`, con fallback alla preferenza di sistema (`prefers-color-scheme`) se non è mai stato impostato nulla; se l'utente è loggato, al primo caricamento successivo di una pagina con sessione attiva viene confrontato con il valore nel database e, in caso di discrepanza, il database viene aggiornato. Il tema scelto prima della registrazione viene salvato come preferenza iniziale al completamento dell'iscrizione. La preferenza di lingua è persistita allo stesso modo per gli studenti, ma al momento non traduce ancora l'interfaccia (nessun sistema i18n implementato).

## Stack tecnologico

| Ambito | Tecnologie |
| --- | --- |
| Backend | Python, Flask, Flask-CORS |
| Autenticazione | Authlib (Google OAuth) |
| Database | SQLAlchemy su SQLite |
| Frontend | HTML/CSS/JS "vanilla" con template Jinja, senza framework né bundler; una coppia HTML/CSS/JS per ciascuna pagina in `resources/html` |
| Servizi geografici esterni | Nominatim (geocoding), Photon (autocompletamento indirizzi), OpenRouteService (routing) |
| Containerizzazione | Docker e Docker Compose per l'avvio coordinato di app principale e geo-proxy |

## Architettura

L'applicazione è composta da due processi Flask indipendenti che comunicano tra loro via HTTP:

- **`app.py`** (porta 5000) — l'app principale: serve le pagine (template Jinja in `resources/html/`), gestisce l'autenticazione e le sessioni utente/azienda ed è l'unico servizio che accede al database. Inoltra le chiamate `/photon` e `/routejson` provenienti dal frontend al geo-proxy.
- **`server.py`** (porta 5001) — un proxy geografico interno, contattato solo da `app.py` (mai direttamente dal browser), che astrae le API esterne di Nominatim (geocoding), Photon (autocompletamento indirizzi) e OpenRouteService (routing).

### Struttura del progetto

```
stageMatch/
├── app.py                  # App principale Flask (porta 5000)
├── server.py                # Geo-proxy Flask (porta 5001)
├── auth/                     # Autenticazione: Google OAuth, sessioni, rate limiter
│   ├── auth.py
│   ├── rate_limiter.py
│   ├── middleware/session_middleware.py
│   └── auth_google/auth.py
├── database/                 # Livello dati SQLAlchemy
│   ├── database_helper.py    # Unico punto di accesso al DB
│   └── models/                # User, Company, UserPreferences, Skill, SoftSkill, UserRoute, PrivacyConsent, ActiveSession
├── resources/                 # Frontend: template Jinja + asset statici (HTML/CSS/JS vanilla)
│   ├── html/                  # Una pagina per file (landing, login, dashboard, mappa, ...)
│   ├── css/                   # Stili, incluse le variabili del design system
│   ├── js/                    # Script lato client, vanilla JS (uno per pagina, con l'eccezione di theme.js)
│   └── img/                   # Immagini e asset statici
├── scripts/                   # Migrazioni one-off dello schema DB (nessun Alembic/Flask-Migrate)
├── ARCHITECTURE.md           # Diagramma del flusso richieste/dati
├── CONTRIBUTING.md           # Regole di branch, commit e Pull Request
├── docker-compose.yml        # Orchestrazione dei due servizi (web + api)
└── requirements.txt
```

`resources/js/theme.js` è l'unica eccezione alla convenzione "un JS per pagina": è caricato da tutte le pagine per applicare il tema chiaro/scuro prima del paint (evitando un flash del tema sbagliato). Su una pagina con sessione utente/azienda attiva legge la preferenza da un meta tag server-side (`<meta name="app-theme" data-role="user|company">`) e, se diverge dal valore in `localStorage`, sincronizza quest'ultimo verso il database tramite `/api/users/preferences/save` o `/api/companies/preferences/save`; sulle pagine pubbliche usa solo `localStorage`, con fallback a `prefers-color-scheme`.

Per il diagramma completo del flusso richieste/dati, consulta [ARCHITECTURE.md](./ARCHITECTURE.md).

## Avvio rapido

Copia `.env.example` in `.env` e compilalo con le tue credenziali, quindi installa le dipendenze:

```bash
pip install -r requirements.txt

python app.py       # app principale — porta 5000
python server.py    # geo-proxy — porta 5001
```

In alternativa, con Docker Compose (avvia entrambi i servizi collegati tra loro):

```bash
docker compose up --build
```

Il login (sia studenti che aziende) richiede credenziali Google OAuth valide (`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`) configurate su Google Cloud Console anche in locale.

### Variabili d'ambiente principali

Le principali variabili sono documentate in `.env.example`:

| Variabile | Descrizione |
| --- | --- |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Credenziali OAuth per il login/registrazione Google di studenti e aziende. |
| `ORS_API_KEY` | API key di OpenRouteService, usata da `server.py` per il calcolo dei percorsi. |
| `SERVER_SECRET_KEY` | Segreto Flask per la firma dei cookie di sessione. |
| `MAX_SESSIONS_PER_USER` / `MAX_SESSIONS_GLOBAL` | Limiti del rate limiter sulle sessioni simultanee. |
| `SESSION_TTL_SECONDS` | Durata (secondi) prima che una sessione inattiva sia considerata scaduta. |
| `DB_CONNECTION_STRING` | Percorso/stringa di connessione del database SQLite. |
| `APP_VERSION` | Versione applicativa mostrata in Impostazioni > Informazioni (default `1.0.0`). |
| `PORT` | Porta di ascolto di `app.py` (default `5000`). Presente in `.env.example`. |
| `PORT_API` | Porta di ascolto di `server.py` (default `5001`). Non è in `.env.example`: va impostata nell'ambiente (lo fa già `docker-compose.yml`) se si vuole un valore diverso dal default. |
| `HOST` | Host di bind per `app.py` e `server.py` (default `127.0.0.1`). Non è in `.env.example`. |

> Nel repository non sono presenti al momento suite di test, linter o build step configurati.

## Contribuire

Leggi [CONTRIBUTING.md](./CONTRIBUTING.md) per branch, commit e Pull Request.

## Licenza e attribuzioni

Il progetto è distribuito sotto licenza Apache License 2.0. Consulta [LICENSE](./LICENSE) per il testo completo.

Le attribuzioni del progetto e dei servizi di terze parti sono raccolte in [NOTICE](./NOTICE).

## Autori

- [Zhoupeng Wu](https://github.com/ZhoupengWu) - sviluppo front-end, back-end e documentazione.
- [Riccardo Bertuletti](https://github.com/Bertu08) - sviluppo front-end.
- [Viktor Kachan](https://github.com/Relunax255) - sviluppo back-end.
