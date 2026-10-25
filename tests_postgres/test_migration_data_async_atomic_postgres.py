"""MIG-DATA-E2E: durable queue and business data share one commit boundary."""
import pytest

# Pytest discovers these fixtures/markers through module globals.
from tests_postgres.test_migration_p0_postgres import (
    ctx as ctx,  # noqa: PLC0414
)
from tests_postgres.test_migration_p0_postgres import (
    pytestmark as pytestmark,  # noqa: PLC0414
)
from tests_postgres.test_migration_p0_postgres import (
    scalar,
)
from tests_postgres.test_migration_p0_postgres import (
    schema as schema,  # noqa: PLC0414
)
from tests_postgres.test_migration_phase3_postgres import (
    queue as queue,  # noqa: PLC0414
)
from tests_postgres.test_migration_phase3_postgres import (
    submit,
)


class SimulatedWorkerExit(BaseException):
    pass


def test_interruption_after_business_commit_already_has_terminal_queue_result(queue, monkeypatch):
    from core.database import get_connection
    from modules.data_migration import service
    job = submit(queue)
    claim = queue['api'].claim(queue['conn'], owner='commit-boundary', lease_seconds=30)
    original = service.run_migration
    def interrupted(*args, **kwargs):
        result = original(*args, **kwargs)
        assert result['status'] == 'completed'
        raise SimulatedWorkerExit()
    monkeypatch.setattr(service, 'run_migration', interrupted)
    with pytest.raises(SimulatedWorkerExit):
        queue['api'].execute_claim(job['id'], 'commit-boundary', claim['attempt'], connection_factory=get_connection)
    persisted = queue['api'].get(queue['conn'], job['id'], queue['actor'])
    assert persisted['status'] == 'completed' and persisted['result_job_id']
    assert persisted['inserted_rows'] == 1
    assert scalar(queue['conn'], 'SELECT count(*) FROM units WHERE company_id=%s', (queue['company_id'],)) == 1


def test_queue_finalize_failure_rolls_back_business_and_legacy_job(queue, monkeypatch):
    from core.database import get_connection
    from modules.companies import service
    job = submit(queue)
    claim = queue['api'].claim(queue['conn'], owner='audit-failure', lease_seconds=30)
    def fail(*args, **kwargs):
        raise RuntimeError('Synthetic audit failure at commit boundary')
    monkeypatch.setattr(service, 'register_company_audit', fail)
    result = queue['api'].execute_claim(job['id'], 'audit-failure', claim['attempt'], connection_factory=get_connection)
    assert result['status'] == 'failed'
    assert scalar(queue['conn'], 'SELECT count(*) FROM units WHERE company_id=%s', (queue['company_id'],)) == 0
    assert scalar(queue['conn'], "SELECT count(*) FROM migration_jobs WHERE company_id=%s AND status='completed'", (queue['company_id'],)) == 0
    persisted = queue['api'].get(queue['conn'], job['id'], queue['actor'])
    assert not persisted.get('result_job_id')


@pytest.mark.parametrize('strategy', ['dry_run', 'arbitrary'])
def test_async_invalid_apply_strategy_never_creates_control_job(queue, strategy):
    with pytest.raises(ValueError):
        queue['api'].submit(queue['conn'], actor=queue['actor'], entity='unidades',
            source_kind='csv', raw=queue['raw'], mapping={'name':'name','unit_type':'unit_type','city':'city'},
            strategy=strategy, request_key='invalid-strategy', preview_token='unused')
    assert scalar(queue['conn'], 'SELECT count(*) FROM migration_async_jobs WHERE company_id=%s', (queue['company_id'],)) == 0


@pytest.mark.parametrize('entity', ['unidades', 'colaboradores', 'epis', 'fornecedores', 'historico_entregas', 'estoque'])
def test_all_six_entities_async_persist_once_and_cancel_safely(queue, entity):
    from core.database import get_connection
    from tests_postgres.test_migration_data_e2e_postgres import (
        ENTITIES,
        encode,
        row_for,
    )
    from tests_postgres.test_migration_p0_postgres import history

    history(queue, strategy='dry_run')
    row = row_for(entity)
    table = ENTITIES[entity][0]
    before = scalar(queue['conn'], f'SELECT count(*) FROM {table} WHERE company_id=%s', (queue['company_id'],))
    args = {'entity': entity, 'raw': encode('csv', [row]), 'mapping': {key: key for key in row}, 'request_key': 'same-http-confirmation'}
    job = submit(queue, **args)
    duplicate = submit(queue, **args)
    assert job['id'] == duplicate['id']
    claim = queue['api'].claim(queue['conn'], owner='six-entities', lease_seconds=30)
    assert claim and claim['id'] == job['id'], claim
    result = queue['api'].execute_claim(job['id'], 'six-entities', claim['attempt'], connection_factory=get_connection)
    assert result['status'] == 'completed', result
    persisted = queue['api'].get(queue['conn'], job['id'], queue['actor'])
    assert persisted['inserted_rows'] == 1 and persisted['processed_rows'] == 1, persisted
    assert scalar(queue['conn'], f'SELECT count(*) FROM {table} WHERE company_id=%s', (queue['company_id'],)) == before + 1
    # Another pending operation can be cancelled without replaying business writes.
    cancelled = submit(queue, **{**args, 'request_key': 'cancel-confirmation'})
    result = queue['api'].request_cancel(queue['conn'], cancelled['id'], queue['actor'])
    assert result['status'] == 'cancelled'
    assert scalar(queue['conn'], f'SELECT count(*) FROM {table} WHERE company_id=%s', (queue['company_id'],)) == before + 1
