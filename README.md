# stageMatch

Un'applicazione web full-stack che abbina i profili degli studenti alle aziende per individuare le opportunità di stage più adatte.

## Descrizione

stageMatch nasce per semplificare l'incontro tra studenti e aziende in cerca di tirocinanti: gli studenti costruiscono un profilo con competenze, preferenze e disponibilità, mentre le aziende pubblicano le proprie opportunità, e l'applicazione si occupa di individuare gli abbinamenti più rilevanti.

L'autenticazione avviene tramite un portale SSO esterno (con fallback su Google OAuth), i dati sono gestiti con SQLAlchemy su SQLite e le funzionalità di geocoding, autocompletamento indirizzi e calcolo dei percorsi sono delegate a un servizio proxy interno dedicato, così da valutare anche la vicinanza geografica tra studente e azienda nel processo di abbinamento.

## Funzionalità principali

- **Profili studente**: dati anagrafici, competenze tecniche (skill) e trasversali (soft skill), preferenze e cronologia degli indirizzi/percorsi cercati.
- **Profili azienda**: registrazione tramite Google OAuth e pubblicazione delle informazioni utili all'abbinamento con gli studenti.
- **Autenticazione a doppio canale**: login tramite il portale SSO d'istituto (JWT) oppure, in alternativa, Google OAuth.
- **Mappa e calcolo percorsi**: ricerca indirizzi con autocompletamento (Photon), geocoding (Nominatim) e calcolo del tragitto casa-azienda (OpenRouteService), il tutto mediato dal servizio geo-proxy interno.
- **Gestione privacy**: tracciamento del consenso privacy per utente, con versionamento della policy (`PRIVACY_POLICY_VERSION`).
- **Controlli di accesso**: whitelist utenti basata su file JSON e rate limiting delle sessioni simultanee (per singolo utente e a livello globale).

## Stack tecnologico

| Ambito | Tecnologie |
| --- | --- |
| Backend | Python, Flask, Flask-CORS, Flask-Login |
| Autenticazione | PyJWT (validazione JWT del portale SSO), Authlib (Google OAuth) |
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
├── auth/                     # Autenticazione: SSO, JWT, whitelist, rate limiter, Google OAuth
│   ├── auth.py
│   ├── middleware/sso_middleware.py
│   └── auth_google/auth.py
├── database/                 # Livello dati SQLAlchemy
│   ├── database_helper.py    # Unico punto di accesso al DB
│   └── models/                # User, Company, UserPreferences, Skill, SoftSkill, UserRoute, PrivacyConsent
├── resources/                 # Frontend: template Jinja + asset statici (HTML/CSS/JS vanilla)
│   ├── html/                  # Una pagina per file (landing, login, dashboard, mappa, ...)
│   └── css/                   # Stili, incluse le variabili del design system
├── ARCHITECTURE.md           # Diagramma del flusso richieste/dati
├── CONTRIBUTING.md           # Regole di branch, commit e Pull Request
├── docker-compose.yml        # Orchestrazione dei due servizi (web + api)
└── requirements.txt
```

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

Per lo sviluppo locale è disponibile una scorciatoia di autenticazione: impostando `SSO_MODE=dev` in `.env`, il login viene simulato senza bisogno del portale SSO reale (vedi `.env.example` per i dettagli).

### Variabili d'ambiente principali

Tutte le variabili sono documentate in `.env.example`; le principali sono:

| Variabile | Descrizione |
| --- | --- |
| `SSO_MODE` | `production` (richiede JWT reale dal portale) o `dev` (login simulato in locale). |
| `DEV_USER_EMAIL` | Email usata per il login automatico in modalità `dev` (sovrascrivibile con `?email=`). |
| `JWT_SECRET` / `APP_AUDIENCE` | Segreto condiviso e audience per la validazione dei JWT emessi dal portale SSO. |
| `PORTAL_URL` | URL del portale SSO usato per i redirect di login/logout. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Credenziali OAuth per il login/registrazione Google. |
| `ORS_API_KEY` | API key di OpenRouteService, usata da `server.py` per il calcolo dei percorsi. |
| `SERVER_SECRET_KEY` | Segreto Flask per la firma dei cookie di sessione. |
| `MAX_SESSIONS_PER_USER` / `MAX_SESSIONS_GLOBAL` | Limiti del rate limiter sulle sessioni simultanee. |
| `DB_CONNECTION_STRING` | Percorso/stringa di connessione del database SQLite. |
| `PORT` / `PORT_API` | Porte di ascolto rispettivamente di `app.py` e `server.py`. |

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
