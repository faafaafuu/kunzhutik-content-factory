"""storefront orders"""

from alembic import op
import sqlalchemy as sa


revision = "20260423_0002"
down_revision = "20260423_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_orders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("customer_name", sa.String(length=160), nullable=False),
        sa.Column("customer_phone", sa.String(length=40), nullable=False),
        sa.Column("delivery_address", sa.String(length=400), nullable=False),
        sa.Column("delivery_slot", sa.String(length=120), nullable=True),
        sa.Column("comment", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="new"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="RUB"),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("items_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("source_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("store_orders")
