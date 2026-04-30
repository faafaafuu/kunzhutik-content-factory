"""storefront payment method"""

from alembic import op
import sqlalchemy as sa


revision = "20260423_0003"
down_revision = "20260423_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "store_orders",
        sa.Column("payment_method", sa.String(length=40), nullable=False, server_default="card_on_delivery"),
    )


def downgrade() -> None:
    op.drop_column("store_orders", "payment_method")
