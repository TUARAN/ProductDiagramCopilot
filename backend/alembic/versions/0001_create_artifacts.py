"""create artifacts

Revision ID: 0001_create_artifacts
Revises: 
Create Date: 2026-01-08

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_create_artifacts"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("kind", sa.String(length=32), nullable=False, index=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="created", index=True),
        sa.Column("request", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("spec", sa.JSON(), nullable=True),
        sa.Column("mermaid", sa.Text(), nullable=True),
        sa.Column("markdown", sa.Text(), nullable=True),
        sa.Column("object_key", sa.String(length=256), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("ix_artifacts_kind", "artifacts", ["kind"], unique=False)
    op.create_index("ix_artifacts_status", "artifacts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_artifacts_status", table_name="artifacts")
    op.drop_index("ix_artifacts_kind", table_name="artifacts")
    op.drop_table("artifacts")
