import os
import sys
import tempfile

# Ambiente di test impostato prima di importare l'app.
os.environ.setdefault("SERVER_SECRET_KEY", "test-secret")
os.environ.setdefault("DB_CONNECTION_STRING", os.path.join(tempfile.mkdtemp(), "app.db"))
os.environ["ANTHROPIC_MATCHING_ENABLED"] = "False"
os.environ["API_URL"] = "http://127.0.0.1:9"
os.environ["ADMIN_EMAILS"] = "admin@example.com"
os.environ["DEBUG"] = "True"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from database import database_helper


@pytest.fixture
def db(tmp_path):
    """Database SQLite pulito per ogni test."""
    database_helper.initDB(str(tmp_path / "test.db"))

    return database_helper


def makeUser(google_id="u1", email="rossi.mario@example.com", **overrides):
    data = {
        "googleId": google_id,
        "name": "Mario",
        "surname": "Rossi",
        "email": email,
        "data_nascita": "2007-01-01",
        "sesso": "M",
        "comune_nascita": "Bergamo",
        "codice_fiscale": "RSSMRA07A01A794X",
        "telefono": "3331112222",
        "indirizzo_studio": "Informatica",
        "classe": "4A",
        "istituto": "ITIS",
        "indirizzo": "Via Roma ££ 1 ££ 24100 ££ Bergamo",
    }
    data.update(overrides)

    return data


def makeCompany(google_id="c1", email="hr@azienda.it", **overrides):
    data = {
        "googleId": google_id,
        "name": "Azienda",
        "email": email,
        "address": "Via Milano ££ 2 ££ 24100 ££ Bergamo",
    }
    data.update(overrides)

    return data
