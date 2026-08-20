"""Bootstrap do banco de dados: orquestra core.schema (DDL) com os
inicializadores de domínio (modules.*) na ordem correta.

Historicamente `init_db()` vivia dentro de core/schema.py e importava
modules.* localmente ali dentro (para provisionar o master admin inicial,
tabelas comerciais/pagamento, backfill de estoque etc.) — isso tornava
core.schema, que deveria ser a camada mais baixa do projeto (só DDL/schema,
sem depender de nenhum módulo de domínio), parte do mesmo ciclo de import
dos módulos que ele deveria só fornecer schema para (CodeQL cyclic import,
issue #148: core.schema -> modules.auth.service -> ... -> core.archival ->
core.schema, entre outras variações do mesmo SCC).

Este módulo é a camada de orquestração que fica ACIMA de core.schema e de
modules.*: chama schema.<ensure_*> para o DDL e os inicializadores de
domínio para seed/backfill, na mesma ordem de antes. Nada importa
core.bootstrap de volta (só app.py/scripts), então ele nunca entra em um
ciclo de import.
"""

from core import schema
from core.database import get_connection as _get_connection
from core.security import hash_password as _hash_password
from epi_backend.config import DB_CONNECTOR_AVAILABLE as _DB_CONNECTOR, DATABASE_URL as _DATABASE_URL
from epi_backend.http_utils import structured_log
from epi_backend.ppe_test_schema import ensure_ppe_test_tables as _ensure_ppe_test_tables
from modules.auth.service import ensure_initial_master_admin as _ensure_admin
from modules.commercial.service import (
    ensure_commercial_settings as _ensure_commercial_settings,
    ensure_commercial_contract_tables as _ensure_commercial_tables,
)
from modules.payments.service import (
    ensure_payment_tables as _ensure_payment_tables,
    ensure_subscription_tables as _ensure_subscription_tables,
)
from modules.settings.service import migrate_module_visibility_unit_model as _migrate_module_visibility
from modules.stock.service import (
    backfill_unit_stock_from_epis as _backfill_stock,
    next_company_qr_sequence as _next_qr_seq,
    build_master_epi_qr as _build_master_qr,
)


def init_db():
    import os as _os
    import time as _time
    from contextlib import closing as _closing
    from datetime import datetime as _datetime, timezone as _timezone
    from epi_backend.unit_jv_lifecycle import (
        ensure_unit_joint_venture_periods_table as _ensure_jv_table,
        import_active_joinventures_from_epis as _import_jv,
    )

    _UTC = _timezone.utc
    retries = int(_os.environ.get('DB_INIT_RETRIES', '8'))
    retry_delay = float(_os.environ.get('DB_INIT_RETRY_DELAY_SECONDS', '2'))
    lock_retries = int(_os.environ.get('DB_INIT_LOCK_RETRIES', '15'))
    lock_retry_delay = float(_os.environ.get('DB_INIT_LOCK_RETRY_DELAY_SECONDS', '1'))
    advisory_lock_key = int(_os.environ.get('DB_INIT_ADVISORY_LOCK_KEY', '83492117'))
    last_error = None
    connection = None
    for attempt in range(1, retries + 1):
        try:
            connection = _get_connection()
            break
        except Exception as exc:
            last_error = exc
            structured_log('warning', 'db.connect_retry', attempt=attempt, retries=retries, error=str(exc))
            if attempt < retries:
                _time.sleep(retry_delay)
    if not connection:
        raise RuntimeError(f'Falha ao conectar no banco após {retries} tentativas: {last_error}')

    with _closing(connection) as connection:
        schema.run_schema_precheck(connection)
        advisory_lock_acquired = False
        if _DB_CONNECTOR and _DATABASE_URL:
            for lock_attempt in range(1, lock_retries + 1):
                try:
                    lock_row = connection.execute(
                        'SELECT pg_try_advisory_lock(?) AS acquired',
                        (advisory_lock_key,)
                    ).fetchone()
                    lock_acquired = bool((lock_row or {}).get('acquired'))
                except Exception as exc:
                    lock_acquired = False
                    structured_log(
                        'warning',
                        'db.init_lock_attempt_failed',
                        attempt=lock_attempt,
                        retries=lock_retries,
                        error=str(exc)
                    )
                if lock_acquired:
                    advisory_lock_acquired = True
                    break
                if lock_attempt < lock_retries:
                    _time.sleep(lock_retry_delay)
            if not advisory_lock_acquired:
                structured_log(
                    'warning',
                    'db.init_lock_not_acquired',
                    retries=lock_retries,
                    lock_key=advisory_lock_key
                )
        connection.executescript(
            '''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                legal_name TEXT NOT NULL DEFAULT '',
                cnpj TEXT NOT NULL UNIQUE,
                logo_type TEXT NOT NULL,
                plan_name TEXT NOT NULL DEFAULT 'Plano padrão',
                user_limit INTEGER NOT NULL DEFAULT 25,
                license_status TEXT NOT NULL DEFAULT 'active',
                active INTEGER NOT NULL DEFAULT 1,
                commercial_notes TEXT NOT NULL DEFAULT '',
                contract_start TEXT NOT NULL DEFAULT '',
                contract_end TEXT NOT NULL DEFAULT '',
                monthly_value REAL NOT NULL DEFAULT 0,
                addendum_enabled INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                company_id INTEGER,
                active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS company_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                actor_user_id INTEGER NOT NULL,
                actor_name TEXT NOT NULL,
                action_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                details_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
            );
            CREATE TABLE IF NOT EXISTS units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                unit_type TEXT NOT NULL,
                city TEXT NOT NULL,
                notes TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                archived_at TEXT,
                archived_by INTEGER,
                archive_reason TEXT NOT NULL DEFAULT '',
                retention_until TEXT,
                legal_hold INTEGER NOT NULL DEFAULT 0,
                legal_hold_reason TEXT NOT NULL DEFAULT '',
                deleted_at TEXT,
                deleted_by INTEGER,
                delete_reason TEXT NOT NULL DEFAULT '',
                UNIQUE(company_id, name),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT
            );
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                employee_id_code TEXT NOT NULL,
                cpf TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '',
                whatsapp TEXT NOT NULL DEFAULT '',
                preferred_contact_channel TEXT NOT NULL DEFAULT 'whatsapp',
                sector TEXT NOT NULL,
                role_name TEXT NOT NULL,
                admission_date TEXT NOT NULL,
                schedule_type TEXT NOT NULL,
                tipo_vinculo TEXT NOT NULL DEFAULT 'CLT',
                empresa_origem TEXT NOT NULL DEFAULT '',
                -- Matrícula é única POR TENANT, mas a chave NÃO é declarada
                -- aqui: quem a cria é `uq_employees_company_employee_code`, em
                -- core/schema.py, que também remove o UNIQUE global antigo das
                -- bases existentes. Um dono só, um nome só — declarar inline
                -- também deixaria toda base nova com dois índices únicos
                -- equivalentes (issue #168).
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT
            );
            CREATE TABLE IF NOT EXISTS epis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                unit_id INTEGER,
                name TEXT NOT NULL,
                purchase_code TEXT NOT NULL,
                ca TEXT NOT NULL,
                sector TEXT NOT NULL,
                epi_section TEXT NOT NULL DEFAULT '',
                stock INTEGER NOT NULL DEFAULT 0,
                unit_measure TEXT NOT NULL,
                ca_expiry TEXT NOT NULL,
                epi_validity_date TEXT NOT NULL,
                manufacture_date TEXT NOT NULL,
                validity_days INTEGER NOT NULL,
                validity_years INTEGER NOT NULL DEFAULT 0,
                validity_months INTEGER NOT NULL DEFAULT 0,
                manufacturer_validity_months INTEGER NOT NULL DEFAULT 0,
                manufacturer TEXT NOT NULL DEFAULT '',
                model_reference TEXT NOT NULL DEFAULT '',
                supplier_company TEXT NOT NULL DEFAULT '',
                manufacturer_recommendations TEXT NOT NULL DEFAULT '',
                epi_photo_data TEXT,
                glove_size TEXT,
                size TEXT,
                uniform_size TEXT,
                joinventures_json TEXT NOT NULL DEFAULT '[]',
                active_joinventure TEXT,
                qr_code_value TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                UNIQUE(company_id, purchase_code),
                UNIQUE(company_id, ca),
                UNIQUE(company_id, qr_code_value),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT
            );
            CREATE TABLE IF NOT EXISTS deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                epi_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                quantity_label TEXT NOT NULL,
                sector TEXT NOT NULL,
                role_name TEXT NOT NULL,
                delivery_date TEXT NOT NULL,
                next_replacement_date TEXT NOT NULL,
                notes TEXT DEFAULT '',
                signature_name TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT
            );
            CREATE TABLE IF NOT EXISTS employee_unit_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                source_unit_id INTEGER NOT NULL,
                target_unit_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                actor_user_id INTEGER NOT NULL,
                actor_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (source_unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (target_unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
            );
            '''
        )
        _ensure_fns = [
            schema.ensure_company_columns,
            schema.ensure_company_audit_columns,
            schema.ensure_tenant_domain_tables,
            schema.ensure_epi_columns,
            schema.ensure_employee_columns,
            schema.ensure_legal_entities,
            # Depende de schema.ensure_legal_entities: usa a FK de companies e o
            # padrão de employees já criado por essa migração.
            schema.ensure_outsourced_companies,
            # Depende de schema.ensure_legal_entities (coluna legal_entity_id) e
            # schema.ensure_outsourced_companies (coluna outsourced_company_id) —
            # limpa legal_entity_id gravado indevidamente em colaborador
            # terceirizado antes da correção do alerta de CNPJ (ADR-0002 §13.7).
            schema.ensure_employee_outsourced_legal_entity_cleanup,
            # Depende de schema.ensure_outsourced_companies (tabela/coluna status
            # precisam existir antes do backfill/lifecycle).
            schema.ensure_outsourced_company_archival_lifecycle_columns,
            # Depende de schema.ensure_outsourced_companies (a coluna precisa da
            # tabela já criada) e de schema.ensure_units_table (indiretamente, via
            # ensure_tenant_domain_tables acima) para a Unidade existir.
            schema.ensure_outsourced_company_unit_scope_column,
            # Depende de schema.ensure_outsourced_companies/ensure_units_table
            # (FKs outsourced_company_id/unit_id) — vínculo operacional por
            # Unidade + pedido de atualização cadastral (extensão ADR-0002 §12).
            schema.ensure_outsourced_company_unit_links,
            schema.ensure_outsourced_company_update_requests,
            # Depende de `employees` (schema.ensure_employee_columns) e de
            # `units`; o backfill vem logo depois da tabela, na mesma ordem.
            schema.ensure_employee_unit_links,
            schema.ensure_employee_unit_links_backfill,
            # Centro de Migração de Dados (ADR-0003) — tabelas próprias,
            # independentes das demais: não dependem de nenhuma entidade de
            # negócio existir, só guardam jobs/registros/mapeamentos.
            schema.ensure_data_migration_tables,
            schema.ensure_employee_simplified_registration_columns,
            schema.ensure_unit_lifecycle_columns,
            schema.ensure_archival_lifecycle_columns,
            schema.ensure_stock_columns,
            schema.ensure_epi_operational_tables,
            # Depois de `schema.ensure_epi_operational_tables`, e não antes: as duas
            # referenciam `epi_requests` e `purchase_requests`, criadas ali. O
            # SQLite aceita FK para tabela inexistente e escondia a inversão;
            # o PostgreSQL recusa, e a criação do banco do zero falhava inteira.
            schema.ensure_stock_reservations,
            schema.ensure_stock_replenishment_needs,
            # Mesma razão de ordem das duas acima: referencia `units` e `epis`.
            schema.ensure_unit_epi_minimum_stock,
            schema.ensure_procurement_supplier_tables,
            _ensure_commercial_settings,
            _ensure_commercial_tables,
            _ensure_payment_tables,
            _ensure_subscription_tables,
            schema.ensure_user_columns,
            schema.ensure_delivery_signature_columns,
            schema.ensure_delivery_handover_columns,
            schema.ensure_delivery_evidence,
            schema.ensure_devolution_columns,
            schema.ensure_delivery_outsourced_snapshot_columns,
            # Depende de `deliveries` e de `migration_jobs` (criada acima em
            # schema.ensure_data_migration_tables) por causa da FK de
            # rastreabilidade da importação.
            schema.ensure_delivery_migration_origin_columns,
            # Depende de deliveries (colunas snapshot acima) e de
            # outsourced_companies (schema.ensure_outsourced_companies, já
            # executada antes na sequência via schema.ensure_legal_entities).
            schema.ensure_epi_reimbursements,
            _ensure_jv_table,
            _ensure_ppe_test_tables,
            schema.ensure_rule_engine_shadow_log,
            schema.ensure_rule_engine_shadow_activated,
            schema.ensure_rule_engine_enforced_all_companies,
            schema.ensure_ubx_golive_declared,
            schema.ensure_drop_legacy_token_columns,
            # Migração idempotente (não é DDL): converte todo
            # configuration_framework:* legado (module_visibility plano +
            # module_unit_scope separado) para o modelo único de
            # module_visibility com override por Unidade.
            _migrate_module_visibility,
        ]
        for _fn in _ensure_fns:
            try:
                structured_log('info', 'db.ensure_fn_started', fn=_fn.__name__)
                _fn(connection)
                connection.commit()
                structured_log('info', 'db.ensure_fn_ok', fn=_fn.__name__)
            except schema.SchemaMigrationError:
                try:
                    connection.rollback()
                except Exception:
                    pass  # melhor esforço: se o rollback falhar, o erro original (relançado abaixo) já basta
                raise
            except Exception as _e:
                try:
                    connection.rollback()
                except Exception:
                    pass  # melhor esforço: se o rollback falhar, SchemaMigrationError abaixo já reporta a causa
                kind = schema._classify_db_error(_e)
                structured_log('error', 'db.ensure_fn_failed', fn=_fn.__name__, error=str(_e), kind=kind)
                raise schema.SchemaMigrationError(
                    f'Falha em migração {_fn.__name__}: {_e}',
                    kind=kind,
                    context={'fn': _fn.__name__, 'phase': 'ensure_fn'},
                ) from _e
        schema.validate_schema_health(connection)
        migration_runtime = schema.run_pending_migrations(connection)
        structured_log(
            'info' if migration_runtime.get('status') == 'ok' else 'warning',
            'db.migration_runner_finished',
            status=migration_runtime.get('status'),
            applied_count=len(migration_runtime.get('applied') or []),
            failed_migration=migration_runtime.get('failed_migration') or '',
        )
        try:
            connection.commit()
        except Exception:
            try:
                connection.rollback()
            except Exception:
                pass  # melhor esforço: connection já está em estado de erro após o commit falhar
        try:
            _companies_count = connection.execute('SELECT COUNT(*) FROM companies').fetchone()[0]
        except Exception as _e:
            structured_log('warning', 'db.select_companies_retry', error=str(_e))
            try:
                connection.rollback()
                _companies_count = connection.execute('SELECT COUNT(*) FROM companies').fetchone()[0]
            except Exception:
                _companies_count = -1
        # Seed de tenants de DEMONSTRAÇÃO (DOF Brasil / Norskan) — DESLIGADO por
        # padrão. No SaaS o banco deve nascer limpo (apenas o master admin de
        # bootstrap criado por _ensure_admin abaixo). Defina SEED_DEMO_TENANTS=1
        # para popular dados de exemplo (dev/teste/legado). Em banco já
        # inicializado (companies != 0) este trecho não roda de qualquer forma.
        _seed_demo = str(_os.environ.get('SEED_DEMO_TENANTS', '')).strip().lower() in ('1', 'true', 'yes', 'on')
        if _seed_demo and _companies_count == 0:
            connection.executemany(
                'INSERT INTO companies (name, legal_name, cnpj, logo_type, plan_name, user_limit, license_status, active, commercial_notes, contract_start, contract_end, monthly_value, addendum_enabled) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                [
                    ('DOF Brasil', 'DOF Subsea Brasil Servicos Ltda', '11.222.333/0001-81', '', 'enterprise', 120, 'active', 1, 'Contrato corporativo ativo.', '2026-01-01', '2026-12-31', 0.0, 0),
                    ('Norskan Offshore', 'Norskan Offshore Ltda', '44.555.666/0001-81', '', 'corporate', 80, 'active', 1, 'Operaçao offshore ativa.', '2026-01-01', '2026-12-31', 0.0, 0),
                ]
            )
        companies = {row['name']: row['id'] for row in connection.execute('SELECT id, name FROM companies').fetchall()}
        connection.execute(
            "UPDATE companies SET cnpj = '11.222.333/0001-81', contract_start = COALESCE(NULLIF(contract_start, ''), '2026-01-01'), contract_end = COALESCE(NULLIF(contract_end, ''), '2026-12-31'), plan_name = CASE WHEN plan_name IN ('Plano padrao', 'Plano padrão', 'Enterprise Offshore') THEN 'enterprise' ELSE plan_name END, logo_type = COALESCE(logo_type, ''), addendum_enabled = COALESCE(addendum_enabled, 0) WHERE name = 'DOF Brasil'"
        )
        connection.execute(
            "UPDATE companies SET cnpj = '44.555.666/0001-81', contract_start = COALESCE(NULLIF(contract_start, ''), '2026-01-01'), contract_end = COALESCE(NULLIF(contract_end, ''), '2026-12-31'), plan_name = CASE WHEN plan_name IN ('Plano padrao', 'Plano padrão', 'Fleet Base') THEN 'corporate' ELSE plan_name END, logo_type = COALESCE(logo_type, ''), addendum_enabled = COALESCE(addendum_enabled, 0) WHERE name = 'Norskan Offshore'"
        )
        connection.execute("UPDATE units SET unit_type = 'embarcacao' WHERE unit_type IN ('navio', 'embarcação')")
        schema.migrate_role_hierarchy(connection)
        try:
            connection.rollback()
        except Exception:
            pass  # melhor esforço: só libera uma transação eventualmente pendente, nada a reportar
        try:
            existing_usernames = {row['username'] for row in connection.execute('SELECT username FROM users').fetchall()}
        except Exception as _e:
            structured_log('warning', 'db.select_users_retry', error=str(_e))
            try:
                connection.rollback()
            except Exception:
                pass  # melhor esforço: a query é reexecutada logo abaixo, o rollback só limpa a transação
            try:
                existing_usernames = {row['username'] for row in connection.execute('SELECT username FROM users').fetchall()}
            except Exception:
                existing_usernames = set()
        users_to_insert = []
        if _seed_demo:
            if 'dof.general' not in existing_usernames:
                users_to_insert.append(('dof.general', _hash_password(_os.environ.get('SEED_DOF_GENERAL_PW', '')), 'Administrador Geral DOF Brasil', 'general_admin', companies['DOF Brasil']))
            if 'dof.admin' not in existing_usernames:
                users_to_insert.append(('dof.admin', _hash_password(_os.environ.get('SEED_DOF_ADMIN_PW', '')), 'Administrador DOF Brasil', 'admin', companies['DOF Brasil']))
            if 'dof.user' not in existing_usernames:
                users_to_insert.append(('dof.user', _hash_password(_os.environ.get('SEED_DOF_PW', '')), 'Usuário DOF Brasil', 'user', companies['DOF Brasil']))
            if 'norskan.general' not in existing_usernames:
                users_to_insert.append(('norskan.general', _hash_password(_os.environ.get('SEED_NORSKAN_GENERAL_PW', '')), 'Administrador Geral Norskan', 'general_admin', companies['Norskan Offshore']))
            if 'norskan.admin' not in existing_usernames:
                users_to_insert.append(('norskan.admin', _hash_password(_os.environ.get('SEED_NORSKAN_ADMIN_PW', '')), 'Administrador Norskan', 'admin', companies['Norskan Offshore']))
            if 'norskan.user' not in existing_usernames:
                users_to_insert.append(('norskan.user', _hash_password(_os.environ.get('SEED_NORSKAN_PW', '')), 'Usuário Norskan Offshore', 'user', companies['Norskan Offshore']))
        if users_to_insert:
            connection.executemany('INSERT INTO users (username, password, full_name, role, company_id) VALUES (?, ?, ?, ?, ?)', users_to_insert)
        bootstrap_admin = _ensure_admin(connection)
        if _seed_demo and connection.execute('SELECT COUNT(*) FROM units').fetchone()[0] == 0:
            connection.executemany(
                'INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (?, ?, ?, ?, ?)',
                [
                    (companies['DOF Brasil'], 'Base Macae', 'base', 'Macae', 'Base onshore'),
                    (companies['DOF Brasil'], 'Navio Skandi', 'navio', 'Bacia de Campos', 'Navio offshore'),
                    (companies['Norskan Offshore'], 'Base Rio Capital', 'base', 'Rio de Janeiro', 'Base onshore'),
                    (companies['Norskan Offshore'], 'Navio Norskan Alpha', 'navio', 'Bacia de Santos', 'Navio offshore'),
                ]
            )
        if _seed_demo and connection.execute('SELECT COUNT(*) FROM employees').fetchone()[0] == 0:
            dof_base = connection.execute("SELECT id FROM units WHERE name = 'Base Macae'").fetchone()['id']
            norskan_ship = connection.execute("SELECT id FROM units WHERE name = 'Navio Norskan Alpha'").fetchone()['id']
            connection.executemany(
                'INSERT INTO employees (company_id, unit_id, employee_id_code, cpf, name, email, whatsapp, preferred_contact_channel, sector, role_name, admission_date, schedule_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                [
                    (companies['DOF Brasil'], dof_base, '1001', '12345678901', 'Carlos Souza', 'carlos.souza@example.com', '55999990001', 'whatsapp', 'Producao', 'Operador', '2025-01-10', '14x14'),
                    (companies['Norskan Offshore'], norskan_ship, '2001', '12345678902', 'Fernanda Lima', 'fernanda.lima@example.com', '55999990002', 'whatsapp', 'SSMA', 'Tecnica de Seguranca', '2024-11-20', '28x28'),
                ]
            )
        if _seed_demo and connection.execute('SELECT COUNT(*) FROM epis').fetchone()[0] == 0:
            dof_base = connection.execute("SELECT id FROM units WHERE name = 'Base Macae'").fetchone()['id']
            norskan_ship = connection.execute("SELECT id FROM units WHERE name = 'Navio Norskan Alpha'").fetchone()['id']
            connection.executemany(
                'INSERT INTO epis (company_id, unit_id, name, purchase_code, ca, sector, stock, unit_measure, ca_expiry, epi_validity_date, manufacture_date, validity_days, qr_code_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                [
                    (companies['DOF Brasil'], dof_base, 'Capacete Classe B', 'COD-001', '12345', 'Producao', 18, 'unidade', '2026-04-25', '2026-10-25', '2025-10-25', 180, f"EPI-{companies['DOF Brasil']}-{dof_base}-COD-001"),
                    (companies['DOF Brasil'], dof_base, 'Bota de Seguranca', 'COD-002', '12346', 'Producao', 12, 'par', '2026-08-01', '2027-02-01', '2025-08-01', 180, f"EPI-{companies['DOF Brasil']}-{dof_base}-COD-002"),
                    (companies['Norskan Offshore'], norskan_ship, 'Luva Nitrilica', 'COD-101', '67890', 'SSMA', 7, 'par', '2026-03-28', '2026-09-28', '2025-09-28', 60, f"EPI-{companies['Norskan Offshore']}-{norskan_ship}-COD-101"),
                ]
            )
        connection.execute(
            "UPDATE epis SET qr_code_value = COALESCE(NULLIF(qr_code_value, ''), 'EPI-' || company_id || '-' || COALESCE(unit_id, 0) || '-' || UPPER(REPLACE(purchase_code, ' ', '-')))"
        )
        seq_rows = connection.execute('SELECT id, company_id FROM epis WHERE epi_master_sequence IS NULL ORDER BY id').fetchall()
        for row in seq_rows:
            seq_value = _next_qr_seq(connection, int(row['company_id']))
            connection.execute(
                "UPDATE epis SET epi_master_sequence = ?, qr_code_value = COALESCE(NULLIF(qr_code_value, ''), ?) WHERE id = ?",
                (seq_value, _build_master_qr(int(row['company_id']), seq_value), int(row['id']))
            )
        _backfill_stock(connection, _datetime.now(_UTC).isoformat())
        _import_jv(connection)
        try:
            connection.execute(
                """
                UPDATE epi_requests SET status = 'separado', last_updated_at = ?
                WHERE status = 'em análise'
                AND id IN (
                    SELECT DISTINCT epi_request_id
                    FROM purchase_request_items
                    WHERE epi_request_id IS NOT NULL
                    AND status IN ('received', 'received_partial', 'checked', 'closed')
                )
                """,
                (_datetime.now(_UTC).isoformat(),)
            )
        except Exception as _mig_e:
            structured_log('warning', 'db.retroactive_epi_request_status_fix', error=str(_mig_e))
        if advisory_lock_acquired:
            try:
                connection.execute('SELECT pg_advisory_unlock(?)', (advisory_lock_key,))
            except Exception as exc:
                structured_log('warning', 'db.init_lock_release_failed', lock_key=advisory_lock_key, error=str(exc))
        connection.commit()
        return bootstrap_admin
