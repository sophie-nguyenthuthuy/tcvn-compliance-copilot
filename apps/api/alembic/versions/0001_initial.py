"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-14 00:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mirrors tcvn_copilot.config.Settings.embedding_dim default.
EMBED_DIM = 1024


def upgrade() -> None:
    # Extensions are also created by postgres-init.sql but keep the migration
    # self-contained for non-Docker deploys.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ---- users ---------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("organization", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ---- standards -----------------------------------------------------
    op.create_table(
        "standards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("title_vi", sa.String(512), nullable=False),
        sa.Column("title_en", sa.String(512)),
        sa.Column("issuer", sa.String(255), nullable=False, server_default="Bộ Xây dựng"),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("issued_at", sa.Date()),
        sa.Column("effective_at", sa.Date()),
        sa.Column(
            "superseded_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("standards.id"),
            nullable=True,
        ),
        sa.Column("description", sa.Text()),
        sa.Column("source_hash", sa.String(128)),
    )
    op.create_index("ix_standards_code", "standards", ["code"])

    # ---- standard_clauses ---------------------------------------------
    op.create_table(
        "standard_clauses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "standard_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("standards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("clause_number", sa.String(64), nullable=False),
        sa.Column("title_vi", sa.String(512)),
        sa.Column("text_vi", sa.Text(), nullable=False),
        sa.Column("text_en", sa.Text()),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("path", sa.String(1024)),
        sa.Column("tags", postgresql.ARRAY(sa.String(64))),
        sa.UniqueConstraint("standard_id", "clause_number", name="uq_clause_per_standard"),
    )
    op.create_index("ix_standard_clauses_standard_id", "standard_clauses", ["standard_id"])
    op.execute(
        "CREATE INDEX ix_clause_text_trgm ON standard_clauses "
        "USING gin (text_vi gin_trgm_ops)"
    )

    # ---- standard_clause_embeddings -----------------------------------
    op.create_table(
        "standard_clause_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "clause_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("standard_clauses.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("dim", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(EMBED_DIM), nullable=False),
    )
    op.execute(
        "CREATE INDEX ix_clause_embedding_hnsw ON standard_clause_embeddings "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )

    # ---- projects ------------------------------------------------------
    op.execute(
        "CREATE TYPE building_type AS ENUM ("
        "'residential','apartment','office','commercial','industrial',"
        "'educational','healthcare','mixed_use','other'"
        ")"
    )
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "building_type",
            postgresql.ENUM(name="building_type", create_type=False),
            nullable=False,
            server_default="other",
        ),
        sa.Column("location", sa.String(255)),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])

    # ---- drawings ------------------------------------------------------
    op.execute("CREATE TYPE drawing_kind AS ENUM ('pdf','dwg','dxf','ifc','image')")
    op.execute(
        "CREATE TYPE drawing_status AS ENUM ('queued','extracting','ready','failed')"
    )
    op.create_table(
        "drawings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("sheet_label", sa.String(64)),
        sa.Column("kind", postgresql.ENUM(name="drawing_kind", create_type=False), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("object_key", sa.String(1024), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="drawing_status", create_type=False),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("error", sa.Text()),
        sa.Column("extracted", postgresql.JSONB()),
    )
    op.create_index("ix_drawings_project_id", "drawings", ["project_id"])
    op.create_index("ix_drawings_status", "drawings", ["status"])

    # ---- compliance_runs ----------------------------------------------
    op.execute(
        "CREATE TYPE run_status AS ENUM ("
        "'queued','running','succeeded','failed','cancelled'"
        ")"
    )
    op.create_table(
        "compliance_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("standards", postgresql.ARRAY(sa.String(64)), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="run_status", create_type=False),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("error", sa.Text()),
        sa.Column("counts", postgresql.JSONB()),
        sa.Column("report_object_key", sa.String(1024)),
    )
    op.create_index("ix_compliance_runs_project_id", "compliance_runs", ["project_id"])
    op.create_index("ix_compliance_runs_status", "compliance_runs", ["status"])

    # ---- compliance_findings ------------------------------------------
    op.execute(
        "CREATE TYPE finding_status AS ENUM ("
        "'non_compliant','likely_non_compliant','needs_review','compliant'"
        ")"
    )
    op.execute(
        "CREATE TYPE finding_severity AS ENUM ('info','low','medium','high','critical')"
    )
    op.create_table(
        "compliance_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("compliance_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "clause_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("standard_clauses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "drawing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drawings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", postgresql.ENUM(name="finding_status", create_type=False), nullable=False),
        sa.Column("severity", postgresql.ENUM(name="finding_severity", create_type=False), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("summary", sa.String(1024), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("remediation", sa.Text()),
        sa.Column("location", postgresql.JSONB()),
        sa.Column("raw", postgresql.JSONB()),
    )
    op.create_index("ix_compliance_findings_run_id", "compliance_findings", ["run_id"])
    op.create_index("ix_compliance_findings_clause_id", "compliance_findings", ["clause_id"])
    op.create_index("ix_compliance_findings_severity", "compliance_findings", ["severity"])


def downgrade() -> None:
    op.drop_table("compliance_findings")
    op.execute("DROP TYPE IF EXISTS finding_severity")
    op.execute("DROP TYPE IF EXISTS finding_status")
    op.drop_table("compliance_runs")
    op.execute("DROP TYPE IF EXISTS run_status")
    op.drop_table("drawings")
    op.execute("DROP TYPE IF EXISTS drawing_status")
    op.execute("DROP TYPE IF EXISTS drawing_kind")
    op.drop_table("projects")
    op.execute("DROP TYPE IF EXISTS building_type")
    op.drop_table("standard_clause_embeddings")
    op.drop_table("standard_clauses")
    op.drop_table("standards")
    op.drop_table("users")
