"""Add day offers table and planner fields

Revision ID: 20240725_0002
Revises: 20240518_0001
Create Date: 2024-07-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

DAY_OF_WEEK_VALUES = ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница")
DAY_OFFER_STATUS_VALUES = ("available", "sold_out", "closed")

revision = "20240725_0002"
down_revision = "20240518_0001"
branch_labels = None
depends_on = None


def _create_enum_type(name: str, values: tuple[str, ...]) -> None:
    literals = ", ".join(f"'{value}'" for value in values)
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{name}') THEN
                    CREATE TYPE {name} AS ENUM ({literals});
                END IF;
            END
            $$;
            """
        )
    )


def upgrade() -> None:
    _create_enum_type("day_offer_day_of_week", DAY_OF_WEEK_VALUES)
    _create_enum_type("day_offer_status", DAY_OFFER_STATUS_VALUES)

    day_enum = postgresql.ENUM(
        *DAY_OF_WEEK_VALUES, name="day_offer_day_of_week", create_type=False
    )
    status_enum = postgresql.ENUM(
        *DAY_OFFER_STATUS_VALUES, name="day_offer_status", create_type=False
    )

    op.create_table(
        "day_offers",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("week_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", day_enum, nullable=False),
        sa.Column("status", status_enum, nullable=False, server_default="available"),
        sa.Column("price_amount", sa.Integer(), nullable=False, server_default="1500"),
        sa.Column("price_currency", sa.String(length=3), nullable=False, server_default="GEL"),
        sa.Column("portion_limit", sa.Integer(), nullable=True),
        sa.Column("portions_reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("calories", sa.Integer(), nullable=True),
        sa.Column("allergens", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("badge", sa.String(length=50), nullable=True),
        sa.Column("order_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("photo_url", sa.String(length=512), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["week_id"], ["menu_weeks.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("week_id", "day_of_week", name="uq_day_offers_week_day"),
    )
    op.create_index(op.f("ix_day_offers_week_id"), "day_offers", ["week_id"], unique=False)

    op.create_table(
        "planner_presets",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False, unique=True),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("days", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("portions", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(op.f("ix_planner_presets_sort_order"), "planner_presets", ["sort_order"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_planner_presets_sort_order"), table_name="planner_presets")
    op.drop_table("planner_presets")

    op.drop_index(op.f("ix_day_offers_week_id"), table_name="day_offers")
    op.drop_table("day_offers")

    op.execute(sa.text("DROP TYPE IF EXISTS day_offer_status"))
    op.execute(sa.text("DROP TYPE IF EXISTS day_offer_day_of_week"))
