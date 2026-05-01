"""Add task metadata fields

Revision ID: 2c4b4e6f901a
Revises: 9f2a7b1e4c3d
Create Date: 2026-05-01 22:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "2c4b4e6f901a"
down_revision = "9f2a7b1e4c3d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ocr_tasks", sa.Column("model_version", sa.String(), nullable=True))
    op.add_column("ocr_tasks", sa.Column("inference_ms", sa.Float(), nullable=True))
    op.add_column("ocr_tasks", sa.Column("avg_confidence", sa.Float(), nullable=True))
    op.add_column("ocr_tasks", sa.Column("image_width", sa.Integer(), nullable=True))
    op.add_column("ocr_tasks", sa.Column("image_height", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("ocr_tasks", "image_height")
    op.drop_column("ocr_tasks", "image_width")
    op.drop_column("ocr_tasks", "avg_confidence")
    op.drop_column("ocr_tasks", "inference_ms")
    op.drop_column("ocr_tasks", "model_version")
