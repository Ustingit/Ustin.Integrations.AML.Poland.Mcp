from aml_poland_mcp.i18n import normalize_language, t


def test_default_language_is_polish() -> None:
    assert t("report.title") == "Karta Oceny Ryzyka Klienta (AML)"


def test_explicit_english() -> None:
    assert t("report.title", "en") == "Client AML Risk Assessment Card"


def test_unsupported_language_falls_back_to_default() -> None:
    assert normalize_language("fr") == "pl"
    assert normalize_language(None) == "pl"
    assert normalize_language("EN") == "en"


def test_interpolation() -> None:
    assert t("tool.krs_not_found", "en", krs="1234567890") == (
        "No entity found for KRS number 1234567890 in the National Court Register."
    )


def test_missing_key_returns_key_itself() -> None:
    assert t("does.not.exist") == "does.not.exist"
