"""add approval task stage

Revision ID: 20260703_0006
Revises: 20260525_0005
Create Date: 2026-07-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260703_0006"
down_revision = "20260525_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("approval_tasks", sa.Column("stage", sa.String(length=16), server_default="video", nullable=False))


def downgrade() -> None:
    op.drop_column("approval_tasks", "stage")
