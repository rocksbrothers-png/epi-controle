"""SQLite development parity. Production DDL is numbered PostgreSQL migration 034."""
SQLITE_DDL = '''
CREATE TABLE IF NOT EXISTS safety_documents (
 id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL REFERENCES companies(id),
 published_version_id INTEGER, archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1)),
 created_at TEXT NOT NULL, created_by INTEGER NOT NULL REFERENCES users(id),
 UNIQUE(id,company_id),
 FOREIGN KEY(published_version_id,id,company_id) REFERENCES safety_document_versions(id,document_id,company_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS safety_document_versions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, document_id INTEGER NOT NULL, company_id INTEGER NOT NULL,
 revision INTEGER NOT NULL CHECK(revision>0), version_label TEXT NOT NULL CHECK(length(trim(version_label))>0),
 title TEXT NOT NULL CHECK(length(trim(title))>0), category TEXT NOT NULL CHECK(category IN ('epi_matrix','glove_matrix','care_guides','use_instructions','technical_manuals','other_sst')),
 effective_date TEXT NOT NULL, all_units INTEGER NOT NULL CHECK(all_units IN (0,1)),
 unit_ids TEXT NOT NULL, sectors TEXT NOT NULL, activities TEXT NOT NULL, epi_ids TEXT NOT NULL,
 original_filename TEXT NOT NULL, original_mime TEXT NOT NULL, original_size INTEGER NOT NULL CHECK(original_size>0 AND original_size<=20971520),
 original_sha256 TEXT NOT NULL, original_content BLOB NOT NULL, manifest TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'draft' CHECK(state IN ('draft','published','superseded','archived')),
 idempotency_key TEXT NOT NULL, request_fingerprint TEXT NOT NULL,
 created_at TEXT NOT NULL, created_by INTEGER NOT NULL REFERENCES users(id),
 UNIQUE(id,document_id,company_id), UNIQUE(id,company_id), UNIQUE(document_id,revision), UNIQUE(company_id,idempotency_key),
 FOREIGN KEY(document_id,company_id) REFERENCES safety_documents(id,company_id),
 CHECK(all_units=1 OR unit_ids<>'[]')
);
CREATE TABLE IF NOT EXISTS safety_preview_pages (
 id INTEGER PRIMARY KEY AUTOINCREMENT, version_id INTEGER NOT NULL, company_id INTEGER NOT NULL,
 part_index INTEGER NOT NULL CHECK(part_index>=0), page_index INTEGER NOT NULL CHECK(page_index>=0),
 content BLOB NOT NULL, UNIQUE(version_id,part_index,page_index),
 FOREIGN KEY(version_id,company_id) REFERENCES safety_document_versions(id,company_id)
);
CREATE TABLE IF NOT EXISTS safety_document_audit (
 id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL REFERENCES companies(id),
 actor_user_id INTEGER REFERENCES users(id), employee_id INTEGER REFERENCES employees(id), unit_id INTEGER REFERENCES units(id),
 document_id INTEGER, version_id INTEGER, action TEXT NOT NULL, decision TEXT NOT NULL CHECK(decision IN ('allow','deny')),
 details TEXT NOT NULL, created_at TEXT NOT NULL,
 FOREIGN KEY(document_id,company_id) REFERENCES safety_documents(id,company_id),
 FOREIGN KEY(version_id,company_id) REFERENCES safety_document_versions(id,company_id)
);
CREATE TABLE IF NOT EXISTS safety_document_policy (
 id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL UNIQUE REFERENCES companies(id),
 allow_admin_original_download INTEGER NOT NULL DEFAULT 0 CHECK(allow_admin_original_download IN (0,1))
);
CREATE INDEX IF NOT EXISTS safety_documents_tenant ON safety_documents(company_id,archived);
CREATE INDEX IF NOT EXISTS safety_versions_document ON safety_document_versions(document_id,revision);
CREATE INDEX IF NOT EXISTS safety_audit_tenant ON safety_document_audit(company_id,created_at);
'''

IMMUTABLE_COLUMNS = ('document_id','company_id','revision','version_label','title','category','effective_date','all_units','unit_ids','sectors','activities','epi_ids','original_filename','original_mime','original_size','original_sha256','original_content','manifest','idempotency_key','request_fingerprint','created_at','created_by')


def ensure_safety_library(connection):
    if not connection.__class__.__module__.startswith('sqlite3'):
        return  # Production has exactly one DDL source: migration 034.
    connection.executescript(SQLITE_DDL)
    for table in ('safety_document_versions', 'safety_preview_pages', 'safety_document_audit'):
        connection.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT,'Immutable document history'); END")
        if table != 'safety_document_versions':
            connection.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT,'Immutable document history'); END")
    condition = ' OR '.join(f'NEW.{name} IS NOT OLD.{name}' for name in IMMUTABLE_COLUMNS)
    connection.execute(f"CREATE TRIGGER IF NOT EXISTS safety_versions_immutable BEFORE UPDATE ON safety_document_versions WHEN {condition} BEGIN SELECT RAISE(ABORT,'Immutable document version'); END")
    connection.execute("""CREATE TRIGGER IF NOT EXISTS safety_versions_state_guard BEFORE UPDATE OF state ON safety_document_versions
        WHEN NEW.state<>OLD.state AND NOT ((OLD.state='draft' AND NEW.state IN ('published','archived')) OR
        (OLD.state='published' AND NEW.state IN ('superseded','archived')) OR (OLD.state='superseded' AND NEW.state='archived'))
        BEGIN SELECT RAISE(ABORT,'Invalid document state transition'); END""")


def production_sql():
    ddl = SQLITE_DDL.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY').replace(' BLOB ', ' BYTEA ')
    # Circular published-version FK is installed after both tables exist.
    ddl = ddl.replace(',\n FOREIGN KEY(published_version_id,id,company_id) REFERENCES safety_document_versions(id,document_id,company_id) DEFERRABLE INITIALLY DEFERRED', '')
    return ddl
