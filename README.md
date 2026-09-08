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
- **Controlli di accesso**: rate limiting delle sessioni simultanee (per singolo utente e a livello globale), persistito su database.

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
│   ├── js/                    # Script lato client, vanilla JS (uno per pagina)
│   └── img/                   # Immagini e asset statici
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
