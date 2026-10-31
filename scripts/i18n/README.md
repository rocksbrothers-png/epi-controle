# I18N verification

These checks use synthetic records and intercept every browser API call. They do not connect to a live tenant, send email or process payments. Browser assertions complement catalogue checks; they do not certify the whole application's translation coverage.

Install `requirements.txt` and `ci/requirements-i18n.txt`, then run `python -m playwright install chromium`.

```sh
pytest tests/test_i18n_engine_runtime.py tests/test_i18n_files_integrity.py tests/test_i18n_pdf_runtime.py tests/test_i18n_alert_metadata.py -q
python scripts/i18n/check_alerts_browser.py --output /tmp/i18n-alerts
python scripts/i18n/check_supplier_portal_browser.py --output /tmp/i18n-supplier
python scripts/i18n/check_library_browser.py --output /tmp/i18n-library
python scripts/i18n/check_connectors_browser.py --output /tmp/i18n-connectors
```

Use `--browser /usr/bin/chromium` for an existing local browser and `--root /path/to/checkout` to select another checkout. Optional `--baseline REVISION` in alert/supplier checks captures that revision's rendering or HTML shell against the current synthetic fixtures; it is not a full historical application deployment. Committed before/after evidence records its original checkpoint separately.

The alert check covers backend presentation metadata, live plurals, dates, size search, escaped original names, keyboard action/context, reading permission and mobile overflow. Supplier checks cover quotation, order, already-answered and invalid-link states in five languages, live form/file preservation, specific errors, success and canonical JSON. Supplier mutations are intercepted responses, not real backend authorization proofs. Existing service tests and PostgreSQL CI retain that responsibility.

The library check runs the isolated converter for a synthetic PNG and exercises admin/portal views, live labels, original values, escaping and mobile layout through intercepted read APIs. It does not replace the full Office/RBAC PostgreSQL workflow.

`scan_html.py` and `scan_js.cjs` produce review candidates. Technical tokens, canonical payload values, logs and dynamic references require classification. Candidate counts are not untranslated-string totals or functional coverage percentages.

The connector check opens the procurement integration modal with intercepted responses.
It verifies registered and custom labels, nested errors, opaque remote diagnostics and live locale changes.
Switching locale never repeats a submission. Invalid, blank and empty JSON configurations retain their existing semantics.
Actor, connector and active values are preserved in submitted bodies.
Use `--baseline REVISION` to run the checks with historical UI assets; failures are retained in JSON and screenshots.
These intercepted requests complement backend scope tests. They never contact or configure a real supplier.
