from auth import auth as au


def test_student_usa_campi_google():
    user = {"given_name": "Maria Grazia", "family_name": "De Luca", "email": "x@gmail.com"}

    assert au.getNameSurname(user) == ("Maria Grazia", "De Luca")


def test_student_ripiega_su_email():
    user = {"email": "rossi.mario.studente@scuola.it"}

    assert au.getNameSurname(user) == ("mario", "rossi")


def test_student_completa_solo_il_campo_mancante():
    user = {"given_name": "Maria Grazia", "email": "deluca.maria.studente@scuola.it"}

    assert au.getNameSurname(user) == ("Maria Grazia", "deluca")


def test_student_email_fuori_formato_non_viene_interpretata():
    for email in ("mario.rossi@gmail.com", "de.luca.mario.studente@scuola.it", "rossi.mario.docente@scuola.it", None):
        assert au.getNameSurname({"email": email}) == ("", "")
