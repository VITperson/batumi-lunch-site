"""Initial schema

Revision ID: 20240518_0001
Revises:
Create Date: 2024-05-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

USER_ROLE_VALUES = ("customer", "admin")
DAY_OF_WEEK_VALUES = ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница")
MENU_DAY_VALUES = DAY_OF_WEEK_VALUES
ORDER_STATUS_VALUES = ("new", "confirmed", "delivered", "cancelled", "cancelled_by_user")
BROADCAST_STATUS_VALUES = ("pending", "running", "completed", "failed")

revision = "20240518_0001"
down_revision = None
branch_labels = None
depends_on = None


user_role_enum = postgresql.ENUM(*USER_ROLE_VALUES, name="user_role", create_type=False)
day_of_week_enum = postgresql.ENUM(*DAY_OF_WEEK_VALUES, name="day_of_week", create_type=False)
menu_day_enum = postgresql.ENUM(*MENU_DAY_VALUES, name="menu_day_of_week", create_type=False)
order_status_enum = postgresql.ENUM(*ORDER_STATUS_VALUES, name="order_status", create_type=False)
broadcast_status_enum = postgresql.ENUM(*BROADCAST_STATUS_VALUES, name="broadcast_status", create_type=False)


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
    _create_enum_type("user_role", USER_ROLE_VALUES)
    _create_enum_type("day_of_week", DAY_OF_WEEK_VALUES)
    _create_enum_type("menu_day_of_week", MENU_DAY_VALUES)
    _create_enum_type("order_status", ORDER_STATUS_VALUES)
    _create_enum_type("broadcast_status", BROADCAST_STATUS_VALUES)

    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True, unique=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True, unique=True),
        sa.Column("role", user_role_enum, nullable=False, server_default="customer"),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "menu_weeks",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("week_label", sa.String(length=128), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=True, unique=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("day_photos", sa.JSON(), nullable=True),
    )

    op.create_table(
        "order_windows",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("next_week_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("week_start", sa.Date(), nullable=True),
    )

    op.create_table(
        "menu_items",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("week_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", menu_day_enum, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["week_id"], ["menu_weeks.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_menu_items_day_of_week"), "menu_items", ["day_of_week"], unique=False)
    op.create_index(op.f("ix_menu_items_week_id"), "menu_items", ["week_id"], unique=False)

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("channels", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column("status", broadcast_status_enum, nullable=False, server_default="pending"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_reason", sa.Text(), nullable=True),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", day_of_week_enum, nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("menu_items", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("status", order_status_enum, nullable=False, server_default="new"),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("delivery_week_start", sa.Date(), nullable=False),
        sa.Column("delivery_date", sa.Date(), nullable=False),
        sa.Column("next_week", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("unit_price", sa.Integer(), nullable=False, server_default="15"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_orders_day_of_week"), "orders", ["day_of_week"], unique=False)
    op.create_index(op.f("ix_orders_delivery_date"), "orders", ["delivery_date"], unique=False)
    op.create_index(op.f("ix_orders_delivery_week_start"), "orders", ["delivery_week_start"], unique=False)
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_delivery_week_start"), table_name="orders")
    op.drop_index(op.f("ix_orders_delivery_date"), table_name="orders")
    op.drop_index(op.f("ix_orders_day_of_week"), table_name="orders")
    op.drop_table("orders")

    op.drop_table("broadcasts")

    op.drop_index(op.f("ix_menu_items_week_id"), table_name="menu_items")
    op.drop_index(op.f("ix_menu_items_day_of_week"), table_name="menu_items")
    op.drop_table("menu_items")

    op.drop_table("order_windows")
    op.drop_table("menu_weeks")
    op.drop_table("users")

    op.execute(sa.text("DROP TYPE IF EXISTS broadcast_status"))
    op.execute(sa.text("DROP TYPE IF EXISTS order_status"))
    op.execute(sa.text("DROP TYPE IF EXISTS menu_day_of_week"))
    op.execute(sa.text("DROP TYPE IF EXISTS day_of_week"))
    op.execute(sa.text("DROP TYPE IF EXISTS user_role"))
