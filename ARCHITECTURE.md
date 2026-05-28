<!--
Copyright 2025-2026 Zhoupeng Wu
Copyright 2025-2026 Riccardo Bertuletti
Copyright 2025-2026 Viktor Kachan

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Application Architecture

```mermaid
graph LR
    classDef frontend fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef backend fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef proxy fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;
    classDef auth fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    classDef db fill:#eceff1,stroke:#263238,stroke-width:2px;
    classDef external fill:#fce4ec,stroke:#880e4f,stroke-width:2px;
    classDef note fill:#fff9c4,stroke:#fbc02d,stroke-width:1px,stroke-dasharray:5 5;

    subgraph Client ["Client Side"]
        FE["Web Frontend<br/>(resources/)"]:::frontend
    end

    subgraph Core ["Core Application (Port 5000)"]
        App["Flask Main App<br/>(app.py)"]:::backend
        SSO["SSO Middleware<br/>(JWT, RateLimit, Whitelist)"]:::auth
        note_app["Serves Views, Sessions,<br/>User Profiles CRUD"]:::note
    end

    subgraph Storage ["Data Layer"]
        ORM["SQLAlchemy ORM"]:::db
        DB[("SQLite Database<br/>(database.db)")]:::db
    end

    subgraph Internal_Proxy ["Internal Proxy (Port 5001)"]
        Server["Flask Geo-Proxy<br/>(server.py)"]:::proxy
        note_server["External API Abstraction<br/>& Coords Processing"]:::note
    end

    subgraph External ["External Services"]
        Portal["SSO Checkin Portal"]:::external
        Photon["Photon API<br/>(Autocomplete)"]:::external
        Nominatim["Nominatim API<br/>(Geocoding)"]:::external
        ORS["OpenRouteService<br/>(Routing)"]:::external
    end

    %% Client Interactions
    FE -->|"1. HTTP Request"| App

    %% Authentication Flow
    App <-->|"2. Auth Flow"| Portal
    App -->|"3. Validation"| SSO

    %% Database Flow
    App -->|"4. Persistence"| ORM
    ORM -->|"5. SQL"| DB

    %% Proxy Flow
    App -->|"6. Internal Proxy"| Server
    
    %% External API Flow
    Server -->|"7a"| Nominatim
    Server -->|"7b"| ORS
    Server -->|"7c"| Photon

    %% Notes
    App -.-> note_app
    Server -.-> note_server
```
