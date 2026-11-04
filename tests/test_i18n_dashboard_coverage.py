import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCALES = ["pt-BR", "en-GB", "es-ES", "fr-FR", "nb-NO"]
DASHBOARD_KEYS = [
    "interactiveLoadingTitle",
    "interactiveLoadingHint",
    "interactiveErrorTitle",
    "interactiveErrorHint",
    "kpiRegion",
    "quickOperationalView",
    "partialSummary",
    "ready",
    "approvedSearchName",
    "approvedSearchProtection",
    "approvedSearchCa",
    "approvedSearchManufacturer",
    "approvedSearchSection",
    "tableEpi",
    "tableManufacturer",
    "tableModelReference",
    "tableCa",
    "tableCaExpiry",
    "tableUsefulLifeMonths",
    "tableProtection",
    "tableSection",
    "tablePhoto",
    "tableRecommendationRestriction",
    "noAlertsFilter",
    "noDeliveriesFilter",
    "noDataFilter",
    "deliveriesThisMonth",
    "returnedDeliveries",
    "registeredEpis",
    "activeEmployees",
    "feedbacks",
    "complaintsPraise",
    "dbPoolUse",
    "dbPoolFree",
    "noCompany",
    "noUnit",
]


def _translations(locale: str) -> dict:
    return json.loads((ROOT / "static" / "i18n" / f"{locale}.json").read_text(encoding="utf-8"))


def test_dashboard_translation_keys_exist_for_all_supported_locales():
    for locale in LOCALES:
        dashboard = _translations(locale).get("dashboard", {})
        missing = [key for key in DASHBOARD_KEYS if not dashboard.get(key)]
        assert not missing, f"{locale} missing dashboard translations: {missing}"


def test_dashboard_translation_values_are_localized_beyond_portuguese():
    pt_dashboard = _translations("pt-BR")["dashboard"]
    for locale in [item for item in LOCALES if item != "pt-BR"]:
        dashboard = _translations(locale)["dashboard"]
        identical = [key for key in DASHBOARD_KEYS if dashboard.get(key) == pt_dashboard.get(key)]
        # Technical acronyms/brand-like labels may intentionally match, but most labels must be localized.
        assert len(identical) <= 6, f"{locale} has too many untranslated dashboard labels: {identical}"


def test_ca_labels_preserve_brazilian_approval_certificate_identity():
    for locale in LOCALES:
        translations = _translations(locale)
        assert translations["dashboard"]["tableCa"] == "CA"
        assert translations["epi"]["caShort"] == "CA"
        labels = [translations["dashboard"][key] for key in
                  ("approvedSearchCa", "tableCaExpiry")]
        labels += [translations["epi"][key] for key in
                   ("ca", "caExpiry", "caNumberHint", "withoutBrazilCa")]
        assert all("CA" in label and "CE" not in label for label in labels)
