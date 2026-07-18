"""Schema do fluxo de Avaliação e Homologação de EPI em Teste.

Tabelas separadas do banco oficial de EPIs aprovados (`epis`). Um EPI em
teste vive em `ppe_test_candidates` (cadastro provisório) até a decisão
formal; somente a homologação transacional cria o registro oficial em
`epis`, preservando o vínculo via `approved_epi_id` / `origin_test_candidate_id`.
"""
from __future__ import annotations


def _exec(connection, sql: str) -> None:
    connection.execute(sql)


def ensure_ppe_test_tables(connection) -> None:
    """Cria as tabelas do fluxo de EPI em teste (idempotente)."""
    _exec(connection, '''
        CREATE TABLE IF NOT EXISTS ppe_test_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            unit_id INTEGER,
            source_type TEXT NOT NULL DEFAULT 'colaborador',
            requester_name TEXT NOT NULL DEFAULT '',
            requester_profile TEXT NOT NULL DEFAULT '',
            employee_id INTEGER,
            employee_registration TEXT NOT NULL DEFAULT '',
            employee_role TEXT NOT NULL DEFAULT '',
            employee_sector TEXT NOT NULL DEFAULT '',
            current_epi_id INTEGER,
            current_epi_issue TEXT NOT NULL DEFAULT '',
            practical_experience TEXT NOT NULL DEFAULT '',
            suggested_name TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            problem_identified TEXT NOT NULL DEFAULT '',
            expected_benefit TEXT NOT NULL DEFAULT '',
            related_activity TEXT NOT NULL DEFAULT '',
            risks TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            attachments_json TEXT NOT NULL DEFAULT '[]',
            suggestion_date TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'recebida',
            triage_result TEXT NOT NULL DEFAULT '',
            triage_checklist_json TEXT NOT NULL DEFAULT '{}',
            triage_notes TEXT NOT NULL DEFAULT '',
            triage_by_user_id INTEGER,
            triage_by_name TEXT NOT NULL DEFAULT '',
            triage_at TEXT NOT NULL DEFAULT '',
            source_feedback_id INTEGER,
            candidate_id INTEGER,
            created_by_user_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE SET NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL
        )
    ''')
    _exec(connection, '''
        CREATE TABLE IF NOT EXISTS ppe_test_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            unit_id INTEGER,
            suggestion_id INTEGER,
            name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT '',
            protection_type TEXT NOT NULL DEFAULT '',
            manufacturer TEXT NOT NULL DEFAULT '',
            model_reference TEXT NOT NULL DEFAULT '',
            supplier TEXT NOT NULL DEFAULT '',
            ca TEXT NOT NULL DEFAULT '',
            ca_expiry TEXT NOT NULL DEFAULT '',
            size TEXT NOT NULL DEFAULT '',
            color TEXT NOT NULL DEFAULT '',
            material TEXT NOT NULL DEFAULT '',
            tech_sheet TEXT NOT NULL DEFAULT '',
            certifications TEXT NOT NULL DEFAULT '',
            test_batch TEXT NOT NULL DEFAULT '',
            quantity_available INTEGER NOT NULL DEFAULT 0,
            unit_measure TEXT NOT NULL DEFAULT 'un',
            estimated_value TEXT NOT NULL DEFAULT '',
            test_cost TEXT NOT NULL DEFAULT '',
            image_data TEXT,
            manual_ref TEXT NOT NULL DEFAULT '',
            technical_doc TEXT NOT NULL DEFAULT '',
            risks_covered TEXT NOT NULL DEFAULT '',
            activities TEXT NOT NULL DEFAULT '',
            restrictions TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'rascunho',
            technical_checklist_json TEXT NOT NULL DEFAULT '{}',
            technical_review_result TEXT NOT NULL DEFAULT '',
            technical_review_notes TEXT NOT NULL DEFAULT '',
            technical_review_by_user_id INTEGER,
            technical_review_by_name TEXT NOT NULL DEFAULT '',
            technical_review_at TEXT NOT NULL DEFAULT '',
            decision TEXT NOT NULL DEFAULT '',
            decision_reason TEXT NOT NULL DEFAULT '',
            decision_by_user_id INTEGER,
            decision_by_name TEXT NOT NULL DEFAULT '',
            decision_at TEXT NOT NULL DEFAULT '',
            technical_opinion TEXT NOT NULL DEFAULT '',
            operational_opinion TEXT NOT NULL DEFAULT '',
            purchasing_opinion TEXT NOT NULL DEFAULT '',
            decision_restrictions TEXT NOT NULL DEFAULT '',
            decision_conditions TEXT NOT NULL DEFAULT '',
            approval_validity TEXT NOT NULL DEFAULT '',
            scope_type TEXT NOT NULL DEFAULT '',
            scope_unit_id INTEGER,
            scope_joint_venture TEXT NOT NULL DEFAULT '',
            approved_epi_id INTEGER,
            homologated_at TEXT NOT NULL DEFAULT '',
            homologated_by_user_id INTEGER,
            homologated_by_name TEXT NOT NULL DEFAULT '',
            created_by_user_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE SET NULL,
            FOREIGN KEY (suggestion_id) REFERENCES ppe_test_suggestions(id) ON DELETE SET NULL,
            FOREIGN KEY (approved_epi_id) REFERENCES epis(id) ON DELETE SET NULL
        )
    ''')
    _exec(connection, '''
        CREATE TABLE IF NOT EXISTS ppe_test_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            objective TEXT NOT NULL DEFAULT '',
            hypothesis TEXT NOT NULL DEFAULT '',
            problem TEXT NOT NULL DEFAULT '',
            risks TEXT NOT NULL DEFAULT '',
            start_date TEXT NOT NULL DEFAULT '',
            end_date TEXT NOT NULL DEFAULT '',
            duration_days INTEGER NOT NULL DEFAULT 0,
            pilot_unit_id INTEGER,
            sector TEXT NOT NULL DEFAULT '',
            activity TEXT NOT NULL DEFAULT '',
            role_name TEXT NOT NULL DEFAULT '',
            participants_target INTEGER NOT NULL DEFAULT 0,
            epis_quantity INTEGER NOT NULL DEFAULT 0,
            current_epi_id INTEGER,
            approval_criteria TEXT NOT NULL DEFAULT '',
            rejection_criteria TEXT NOT NULL DEFAULT '',
            evaluation_frequency TEXT NOT NULL DEFAULT '',
            technical_manager TEXT NOT NULL DEFAULT '',
            operational_manager TEXT NOT NULL DEFAULT '',
            training_required INTEGER NOT NULL DEFAULT 0,
            contingency_plan TEXT NOT NULL DEFAULT '',
            interruption_condition TEXT NOT NULL DEFAULT '',
            min_participants INTEGER NOT NULL DEFAULT 0,
            min_response_rate INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(candidate_id),
            FOREIGN KEY (candidate_id) REFERENCES ppe_test_candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (pilot_unit_id) REFERENCES units(id) ON DELETE SET NULL,
            FOREIGN KEY (current_epi_id) REFERENCES epis(id) ON DELETE SET NULL
        )
    ''')
    _exec(connection, '''
        CREATE TABLE IF NOT EXISTS ppe_test_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            unit_id INTEGER,
            employee_id INTEGER NOT NULL,
            role_name TEXT NOT NULL DEFAULT '',
            current_epi_id INTEGER,
            size TEXT NOT NULL DEFAULT '',
            delivered_at TEXT NOT NULL DEFAULT '',
            orientation_confirmed INTEGER NOT NULL DEFAULT 0,
            signature_name TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'convidado',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(candidate_id, employee_id),
            FOREIGN KEY (candidate_id) REFERENCES ppe_test_candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE SET NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            FOREIGN KEY (current_epi_id) REFERENCES epis(id) ON DELETE SET NULL
        )
    ''')
    _exec(connection, '''
        CREATE TABLE IF NOT EXISTS ppe_test_distributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            participant_id INTEGER,
            movement_type TEXT NOT NULL DEFAULT 'entrega',
            quantity INTEGER NOT NULL DEFAULT 1,
            batch TEXT NOT NULL DEFAULT '',
            supplier TEXT NOT NULL DEFAULT '',
            storage_location TEXT NOT NULL DEFAULT '',
            responsible_name TEXT NOT NULL DEFAULT '',
            signature_name TEXT NOT NULL DEFAULT '',
            expected_return TEXT NOT NULL DEFAULT '',
            disposal_required INTEGER NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT '',
            created_by_user_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (candidate_id) REFERENCES ppe_test_candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (participant_id) REFERENCES ppe_test_participants(id) ON DELETE SET NULL
        )
    ''')
    _exec(connection, '''
        CREATE TABLE IF NOT EXISTS ppe_test_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            participant_id INTEGER NOT NULL,
            stage TEXT NOT NULL DEFAULT 'inicial',
            ratings_json TEXT NOT NULL DEFAULT '{}',
            current_epi_ratings_json TEXT NOT NULL DEFAULT '{}',
            comments TEXT NOT NULL DEFAULT '',
            positive_points TEXT NOT NULL DEFAULT '',
            negative_points TEXT NOT NULL DEFAULT '',
            preference TEXT NOT NULL DEFAULT '',
            recommend INTEGER NOT NULL DEFAULT 0,
            issues TEXT NOT NULL DEFAULT '',
            continue_intent INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (candidate_id) REFERENCES ppe_test_candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (participant_id) REFERENCES ppe_test_participants(id) ON DELETE CASCADE
        )
    ''')
    _exec(connection, '''
        CREATE TABLE IF NOT EXISTS ppe_test_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            participant_id INTEGER,
            incident_type TEXT NOT NULL DEFAULT 'desconforto',
            severity TEXT NOT NULL DEFAULT 'leve',
            description TEXT NOT NULL DEFAULT '',
            evidence TEXT NOT NULL DEFAULT '',
            photo_data TEXT,
            action_taken TEXT NOT NULL DEFAULT '',
            responsible_name TEXT NOT NULL DEFAULT '',
            conclusion_notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'aberta',
            suspended_test INTEGER NOT NULL DEFAULT 0,
            created_by_user_id INTEGER,
            created_at TEXT NOT NULL,
            resolved_at TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (candidate_id) REFERENCES ppe_test_candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (participant_id) REFERENCES ppe_test_participants(id) ON DELETE SET NULL
        )
    ''')
    _exec(connection, '''
        CREATE TABLE IF NOT EXISTS ppe_test_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            suggestion_id INTEGER,
            company_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            previous_status TEXT NOT NULL DEFAULT '',
            new_status TEXT NOT NULL DEFAULT '',
            actor_user_id INTEGER,
            actor_name TEXT NOT NULL DEFAULT '',
            actor_role TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (candidate_id) REFERENCES ppe_test_candidates(id) ON DELETE CASCADE,
            FOREIGN KEY (suggestion_id) REFERENCES ppe_test_suggestions(id) ON DELETE CASCADE,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        )
    ''')
    _exec(connection, 'CREATE INDEX IF NOT EXISTS idx_ppe_suggestions_company ON ppe_test_suggestions (company_id, status)')
    _exec(connection, 'CREATE INDEX IF NOT EXISTS idx_ppe_candidates_company ON ppe_test_candidates (company_id, status)')
    _exec(connection, 'CREATE INDEX IF NOT EXISTS idx_ppe_participants_candidate ON ppe_test_participants (candidate_id, status)')
    _exec(connection, 'CREATE INDEX IF NOT EXISTS idx_ppe_distributions_candidate ON ppe_test_distributions (candidate_id)')
    _exec(connection, 'CREATE INDEX IF NOT EXISTS idx_ppe_evaluations_candidate ON ppe_test_evaluations (candidate_id, stage)')
    _exec(connection, 'CREATE INDEX IF NOT EXISTS idx_ppe_incidents_candidate ON ppe_test_incidents (candidate_id, status)')
    _exec(connection, 'CREATE INDEX IF NOT EXISTS idx_ppe_events_candidate ON ppe_test_events (candidate_id, created_at)')
    # Vínculo reverso no banco oficial: de onde veio o EPI homologado.
    # approval_scope_type é metadado de auditoria — a visibilidade continua
    # derivada de (unit_id, JV ativa) pela regra C1+D1+E3 (epi_backend/epi_scope.py).
    # Usa o helper portátil _safe_add_column (SQLite + PostgreSQL) — PRAGMA é
    # exclusivo do SQLite e quebraria o boot em produção (Postgres).
    from core.schema import _safe_add_column
    _safe_add_column(connection, 'epis', 'origin_test_candidate_id', 'INTEGER')
    _safe_add_column(connection, 'epis', 'approval_scope_type', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epis', 'homologated_at', "TEXT NOT NULL DEFAULT ''")
