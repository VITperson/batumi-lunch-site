"""Add order templates tables

Revision ID: 20240725_0003
Revises: 20240725_0002
Create Date: 2024-07-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20240725_0003"
down_revision = "20240725_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_templates",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("base_week_start", sa.Date(), nullable=True),
        sa.Column("weeks_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("repeat_weeks", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("promo_code", sa.String(length=32), nullable=True),
        sa.Column("subtotal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="GEL"),
        sa.Column("delivery_zone", sa.String(length=64), nullable=True),
        sa.Column("delivery_available", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        op.f("ix_order_templates_user_id"),
        "order_templates",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "order_template_weeks",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("template_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("week_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("week_start", sa.Date(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("menu_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("label", sa.String(length=64), nullable=True),
        sa.Column("subtotal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("selections", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("items", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("warnings", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.ForeignKeyConstraint(["template_id"], ["order_templates.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_order_template_weeks_template_id"),
        "order_template_weeks",
        ["template_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_order_template_weeks_template_index",
        "order_template_weeks",
        ["template_id", "week_index"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_order_template_weeks_template_index",
        "order_template_weeks",
        type_="unique",
    )
    op.drop_index(op.f("ix_order_template_weeks_template_id"), table_name="order_template_weeks")
    op.drop_table("order_template_weeks")

    op.drop_index(op.f("ix_order_templates_user_id"), table_name="order_templates")
    op.drop_table("order_templates")
