-- Bootstrap script for the development Postgres container.
-- Idempotent; runs on first container start.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Vietnamese-aware text search config (unaccented + simple stemming).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'vietnamese') THEN
        CREATE TEXT SEARCH CONFIGURATION vietnamese (COPY = simple);
        ALTER TEXT SEARCH CONFIGURATION vietnamese
            ALTER MAPPING FOR hword, hword_part, word
            WITH unaccent, simple;
    END IF;
END
$$;
