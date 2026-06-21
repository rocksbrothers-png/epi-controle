from scripts.flutter_migration_audit import run_audit


def test_roadmap_foundation_and_architecture_guardrails_are_present():
    checks = run_audit()
    failures = [check for check in checks if check.status != 'ok']
    assert not failures, [f'{check.phase}:{check.target}:{check.status}' for check in failures]


def test_all_executive_roadmap_modules_are_covered_by_audit():
    checks = run_audit()
    targets = {(check.phase, check.target) for check in checks}
    for module in ['employees', 'stock', 'deliveries', 'purchases', 'reports']:
        assert ('2-multi-tenant', module) in targets
        assert (f'3-7-{module}', 'estrutura-alvo') in targets
