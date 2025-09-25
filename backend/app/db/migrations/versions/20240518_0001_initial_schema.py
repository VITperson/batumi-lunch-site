"""Initial database schema."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20240518_0001"
down_revision = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column(
            "roles",
            sa.JSON(),
            nullable=False,
            server_default=sa.text('\"[\\"customer\\"]\"'),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=False)
    op.create_index(op.f("ix_user_telegram_id"), "user", ["telegram_id"], unique=False)

    op.create_table(
        "menuweek",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("hero_image_url", sa.String(length=512), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("week_start"),
    )
    op.create_index(op.f("ix_menuweek_week_start"), "menuweek", ["week_start"], unique=False)

    op.create_table(
        "orderwindow",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("week_start", sa.Date(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "menuitem",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("menu_week_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day", sa.String(length=16), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["menu_week_id"], ["menuweek.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_menu_items_week_day_position", "menuitem", ["menu_week_id", "day", "position"], unique=False)

    op.create_table(
        "broadcast",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channels", sa.JSON(), nullable=False, server_default=sa.text('\"[]\"')),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("html_body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("sent", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["user.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "order",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("menu_week_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("day", sa.String(length=16), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("menu_snapshot", sa.JSON(), nullable=True),
        sa.Column("address_snapshot", sa.Text(), nullable=True),
        sa.Column("phone_snapshot", sa.String(length=32), nullable=True),
        sa.Column("delivery_week_start", sa.Date(), nullable=False),
        sa.Column("is_next_week", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["menu_week_id"], ["menuweek.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index(op.f("ix_order_public_id"), "order", ["public_id"], unique=False)
    op.create_index("ix_orders_week_status", "order", ["delivery_week_start", "status"], unique=False)
    op.create_index("ix_orders_user_day_week", "order", ["user_id", "day", "delivery_week_start"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_orders_user_day_week", table_name="order")
    op.drop_index("ix_orders_week_status", table_name="order")
    op.drop_index(op.f("ix_order_public_id"), table_name="order")
    op.drop_table("order")
    op.drop_table("broadcast")
    op.drop_index("ix_menu_items_week_day_position", table_name="menuitem")
    op.drop_table("menuitem")
    op.drop_table("orderwindow")
    op.drop_index(op.f("ix_menuweek_week_start"), table_name="menuweek")
    op.drop_table("menuweek")
    op.drop_index(op.f("ix_user_telegram_id"), table_name="user")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
