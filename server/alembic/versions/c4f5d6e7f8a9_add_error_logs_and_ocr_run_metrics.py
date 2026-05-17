"""Add error_logs and ocr_run_metrics for business-aware monitoring

Revision ID: c4f5d6e7f8a9
Revises: b2d8e9f1a4c5
Create Date: 2026-05-08
"""

from alembic import op
import sqlalchemy as sa


revision = "c4f5d6e7f8a9"
down_revision = "b2d8e9f1a4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "error_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("error_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["ocr_tasks.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_error_logs_id"), "error_logs", ["id"], unique=False)
    op.create_index(op.f("ix_error_logs_error_type"), "error_logs", ["error_type"], unique=False)
    op.create_index(op.f("ix_error_logs_task_id"), "error_logs", ["task_id"], unique=False)
    op.create_index(op.f("ix_error_logs_user_id"), "error_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_error_logs_created_at"), "error_logs", ["created_at"], unique=False)

    op.create_table(
        "ocr_run_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("http_latency_ms", sa.Float(), nullable=True),
        sa.Column("image_size_bytes", sa.Integer(), nullable=True),
        sa.Column("inference_ms", sa.Float(), nullable=True),
        sa.Column("avg_confidence", sa.Float(), nullable=True),
        sa.Column("image_width", sa.Integer(), nullable=True),
        sa.Column("image_height", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["ocr_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ocr_run_metrics_id"), "ocr_run_metrics", ["id"], unique=False)
    op.create_index(op.f("ix_ocr_run_metrics_task_id"), "ocr_run_metrics", ["task_id"], unique=True)
    op.create_index(op.f("ix_ocr_run_metrics_owner_id"), "ocr_run_metrics", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ocr_run_metrics_owner_id"), table_name="ocr_run_metrics")
    op.drop_index(op.f("ix_ocr_run_metrics_task_id"), table_name="ocr_run_metrics")
    op.drop_index(op.f("ix_ocr_run_metrics_id"), table_name="ocr_run_metrics")
    op.drop_table("ocr_run_metrics")
    op.drop_index(op.f("ix_error_logs_created_at"), table_name="error_logs")
    op.drop_index(op.f("ix_error_logs_user_id"), table_name="error_logs")
    op.drop_index(op.f("ix_error_logs_task_id"), table_name="error_logs")
    op.drop_index(op.f("ix_error_logs_error_type"), table_name="error_logs")
    op.drop_index(op.f("ix_error_logs_id"), table_name="error_logs")
    op.drop_table("error_logs")
