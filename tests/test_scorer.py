from matching import scorer


def test_skill_score_no_requirements_is_neutral():
    assert scorer._skillScore([{"name": "Python", "livello": 3}], []) == scorer.NEUTRAL_SCORE_NO_REQUIREMENTS


def test_skill_score_missing_skill_is_zero():
    assert scorer._skillScore([], [{"name": "Python", "livello_min": 2}]) == 0.0


def test_skill_score_level_met_or_exceeded():
    assert scorer._skillScore([{"name": "Python", "livello": 3}], [{"name": "Python", "livello_min": 2}]) == 1.0


def test_skill_score_lower_level_is_proportional():
    score = scorer._skillScore([{"name": "Python", "livello": 1}], [{"name": "Python", "livello_min": 3}])

    assert round(score, 2) == 0.33


def test_skill_score_ignores_case_accents_and_spaces():
    student = [{"name": " Gestione Élite ", "livello": 2}]

    assert scorer._skillScore(student, [{"name": "gestione elite", "livello_min": 2}]) == 1.0


def test_skill_score_duplicate_names_keep_highest_level():
    student = [{"name": "python", "livello": 1}, {"name": "Python", "livello": 3}]

    assert scorer._skillScore(student, [{"name": "PYTHON", "livello_min": 3}]) == 1.0


def test_skill_score_zero_or_missing_livello_min_does_not_crash():
    student = [{"name": "Python", "livello": 2}]

    assert scorer._skillScore(student, [{"name": "Python", "livello_min": 0}]) == 1.0
    assert scorer._skillScore(student, [{"name": "Python"}]) == 1.0


def test_soft_skill_score():
    student = [{"label": "Teamwork"}, {"label": "Empatia"}]

    assert scorer._softSkillScore(student, []) == scorer.NEUTRAL_SCORE_NO_REQUIREMENTS
    assert scorer._softSkillScore(student, [{"label": "teamwork"}, {"label": "Leadership"}]) == 0.5


def test_distance_score_bounds():
    assert scorer._distanceScore(0) == 1.0
    assert scorer._distanceScore(30) == 0.5
    assert scorer._distanceScore(60) == 0.0
    assert scorer._distanceScore(600) == 0.0


def test_unknown_distance_never_beats_a_known_medium_trip():
    assert scorer._distanceScore(None) < scorer._distanceScore(20)


def test_compute_deterministic_score_full_match():
    result = scorer.computeDeterministicScore(
        [{"name": "Python", "livello": 3}], [{"label": "Teamwork"}],
        1.0, 0.0,
        [{"name": "Python", "livello_min": 2}], [{"label": "Teamwork"}],
    )

    assert result["score"] == 100.0
    assert result["has_skill_requirements"] is True


def test_compute_deterministic_score_without_requirements_is_not_inflated():
    result = scorer.computeDeterministicScore([], [], None, None, [], [])

    assert result["score"] < 50
    assert result["has_skill_requirements"] is False
