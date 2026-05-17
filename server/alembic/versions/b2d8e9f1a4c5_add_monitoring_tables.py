"""Add system_logs and data_backup_records for monitoring

Revision ID: b2d8e9f1a4c5
Revises: 9f2a7b1e4c3d
Create Date: 2026-05-08 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "b2d8e9f1a4c5"
down_revision = "9f2a7b1e4c3d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("path", sa.String(length=512), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_system_logs_id"), "system_logs", ["id"], unique=False)
    op.create_index(op.f("ix_system_logs_level"), "system_logs", ["level"], unique=False)
    op.create_index(op.f("ix_system_logs_source"), "system_logs", ["source"], unique=False)
    op.create_index(op.f("ix_system_logs_created_at"), "system_logs", ["created_at"], unique=False)

    op.create_table(
        "data_backup_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_data_backup_records_id"), "data_backup_records", ["id"], unique=False)
    op.create_index(op.f("ix_data_backup_records_created_at"), "data_backup_records", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_data_backup_records_created_at"), table_name="data_backup_records")
    op.drop_index(op.f("ix_data_backup_records_id"), table_name="data_backup_records")
    op.drop_table("data_backup_records")
    op.drop_index(op.f("ix_system_logs_created_at"), table_name="system_logs")
    op.drop_index(op.f("ix_system_logs_source"), table_name="system_logs")
    op.drop_index(op.f("ix_system_logs_level"), table_name="system_logs")
    op.drop_index(op.f("ix_system_logs_id"), table_name="system_logs")
    op.drop_table("system_logs")
