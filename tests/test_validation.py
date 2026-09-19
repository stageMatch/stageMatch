import pytest

import validation


def test_clean_text_rules():
    assert validation.cleanText("  ciao ", "campo") == "ciao"
    assert validation.cleanText("   ", "campo") is None
    assert validation.cleanText(None, "campo") is None

    with pytest.raises(ValueError):
        validation.cleanText("", "campo", required=True)

    with pytest.raises(ValueError):
        validation.cleanText("x" * 201, "campo")

    with pytest.raises(ValueError):
        validation.cleanText({"a": 1}, "campo")


@pytest.mark.parametrize("value, expected", [
    ("example.com", "https://example.com"),
    ("http://example.com/a?b=1", "http://example.com/a?b=1"),
    ("", None),
])
def test_normalize_website_accepts(value, expected):
    assert validation.normalizeWebsite(value) == expected


@pytest.mark.parametrize("value", [
    'x" onmouseover="alert(1)',
    "javascript:alert(1)",
    "https://a.com/<script>",
    "ftp://example.com",
])
def test_normalize_website_rejects_dangerous_values(value):
    with pytest.raises(ValueError):
        validation.normalizeWebsite(value)


def test_normalize_skills_dedup_keeps_highest_and_checks_range():
    result = validation.normalizeSkills([
        {"name": "Python", "livello": 1},
        {"name": "python", "livello": "3"},
    ])

    assert result == [{"name": "python", "livello": 3}]

    for bad in ([{"name": "x", "livello": 4}], [{"name": "x"}], [{"livello": 1}], "no", [1]):
        with pytest.raises(ValueError):
            validation.normalizeSkills(bad)


def test_normalize_languages_levels():
    assert validation.normalizeLanguages([{"name": "Inglese", "level": "B2"}])[0]["level"] == "B2"

    with pytest.raises(ValueError):
        validation.normalizeLanguages([{"name": "Inglese", "level": "Z9"}])


def test_normalize_experiences_link_is_sanitized():
    with pytest.raises(ValueError):
        validation.normalizeExperiences([{"title": "x", "link": "javascript:alert(1)"}])

    result = validation.normalizeExperiences([{"title": "Progetto", "link": "github.com/x", "labels": [" a ", ""]}])

    assert result[0]["link"] == "https://github.com/x"
    assert result[0]["labels"] == ["a"]


def test_job_offer_requires_title_only_on_create():
    with pytest.raises(ValueError):
        validation.normalizeJobOffer({"title": " "}, require_title=True)

    assert validation.normalizeJobOffer({"description": "d"}, require_title=False) == {"description": "d"}


def test_company_profile_sito_web_and_name():
    assert validation.normalizeCompanyProfile({"sito_web": "acme.it"})["sito_web"] == "https://acme.it"

    with pytest.raises(ValueError):
        validation.normalizeCompanyProfile({"name": ""})
