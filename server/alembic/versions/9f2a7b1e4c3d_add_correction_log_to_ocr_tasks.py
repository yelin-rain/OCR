"""Add correction_log to ocr_tasks

Revision ID: 9f2a7b1e4c3d
Revises: c0ef369c371a
Create Date: 2026-05-01 21:32:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9f2a7b1e4c3d"
down_revision = "c0ef369c371a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ocr_tasks", sa.Column("correction_log", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ocr_tasks", "correction_log")
