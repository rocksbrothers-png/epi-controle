-- Migration: companies white-label & multi-tenant fields
-- Adds slug, subdomain, custom_domain, colors, language and branding columns
-- to the companies table. All columns are idempotent (IF NOT EXISTS).

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS slug             TEXT,
  ADD COLUMN IF NOT EXISTS subdomain        TEXT,
  ADD COLUMN IF NOT EXISTS custom_domain    TEXT,
  ADD COLUMN IF NOT EXISTS login_logo_type  TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS primary_color    TEXT NOT NULL DEFAULT '#1565C0',
  ADD COLUMN IF NOT EXISTS secondary_color  TEXT NOT NULL DEFAULT '#42A5F5',
  ADD COLUMN IF NOT EXISTS accent_color     TEXT NOT NULL DEFAULT '#FF6F00',
  ADD COLUMN IF NOT EXISTS default_language TEXT NOT NULL DEFAULT 'pt-BR',
  ADD COLUMN IF NOT EXISTS favicon_type     TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS institutional_message TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS contact_email    TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS contact_phone    TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS website          TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS theme_json       TEXT NOT NULL DEFAULT '{}';

-- Unique indexes for tenant routing (only on non-null values)
CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_slug
  ON companies (slug)
  WHERE slug IS NOT NULL AND slug <> '';

CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_subdomain
  ON companies (subdomain)
  WHERE subdomain IS NOT NULL AND subdomain <> '';

CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_custom_domain
  ON companies (custom_domain)
  WHERE custom_domain IS NOT NULL AND custom_domain <> '';

-- Back-fill slug from existing company names (lower-case, hyphens, no diacritics)
-- Only sets slug where it is currently NULL
UPDATE companies
SET slug = lower(
  regexp_replace(
    regexp_replace(
      translate(name,
        'àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ',
        'aaaaaaceeeeiiiinoooooouuuuyby'
      ),
      '[^a-z0-9]+', '-', 'g'
    ),
    '^-+|-+$', '', 'g'
  )
)
WHERE slug IS NULL OR slug = '';
