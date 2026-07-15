"""Add meal configuration.

Revision ID: b01c2d3e4f5a
Revises: a09a8abf038c
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b01c2d3e4f5a"

down_revision: Union[str, None] = (
    "a09a8abf038c"
)

branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None

depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    op.create_table(
        "meal_config",

        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),

        sa.Column(
            "machine_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "meal_name",
            sa.String(length=20),
            nullable=False,
        ),

        sa.Column(
            "start_time",
            sa.Time(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["machine_id"],
            ["machines.id"],
            name="fk_meal_config_machine_id",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "machine_id",
            "meal_name",
            name="uq_machine_meal_name",
        ),
    )

    op.create_index(
        "ix_meal_config_machine_id",
        "meal_config",
        ["machine_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meal_config_machine_id",
        table_name="meal_config",
    )

    op.drop_table("meal_config")