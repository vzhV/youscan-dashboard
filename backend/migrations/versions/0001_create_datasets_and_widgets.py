"""create datasets and widgets

Revision ID: 0001
Revises:
Create Date: 2026-10-27 20:41:58.035755
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("origin", sa.Enum("seed", "upload", "generated", name="dataset_origin"), nullable=False),
        sa.Column(
            "chart_type", sa.Enum("line", "bar", "stacked_bar", "pie", name="chart_type"), nullable=False
        ),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("source_sheet", sa.String(length=255), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("display_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_datasets")),
    )
    op.create_table(
        "widgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "type", sa.Enum("line", "bar", "stacked_bar", "pie", "text", name="widget_type"), nullable=False
        ),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(type = 'text') = (dataset_id IS NULL)", name=op.f("ck_widgets_text_iff_no_dataset")
        ),
        sa.CheckConstraint(
            "type = 'text' OR text_content IS NULL", name=op.f("ck_widgets_text_content_only_for_text")
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["datasets.id"], name=op.f("fk_widgets_dataset_id_datasets"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_widgets")),
    )
    op.create_index("ix_widgets_dataset_id", "widgets", ["dataset_id"], unique=False)
    op.create_index("ix_widgets_position", "widgets", ["position"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_widgets_position", table_name="widgets")
    op.drop_index("ix_widgets_dataset_id", table_name="widgets")
    op.drop_table("widgets")
    op.drop_table("datasets")
    # Postgres enum types outlive their tables, so they are dropped explicitly.
    sa.Enum(name="widget_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="chart_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="dataset_origin").drop(op.get_bind(), checkfirst=True)
