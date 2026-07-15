"""add multi machine support

Revision ID: a09a8abf038c
Revises: 0001
Create Date: 2026-07-14 10:22:49.109664
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a09a8abf038c"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # Machines
    # ---------------------------------------------------------

    op.create_table(
        "machines",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "machine_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "machine_code",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_machines_machine_code",
        "machines",
        ["machine_code"],
        unique=True,
    )

    # Existing data belongs to this machine.
    op.execute(
        """
        INSERT INTO machines (
            machine_name,
            machine_code,
            is_active
        )
        VALUES (
            'Weldomat',
            'WELDOMAT-01',
            TRUE
        )
        """
    )

    # ---------------------------------------------------------
    # Machine events
    # ---------------------------------------------------------

    op.add_column(
        "machine_events",
        sa.Column(
            "machine_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE machine_events
        SET machine_id = (
            SELECT id
            FROM machines
            WHERE machine_code = 'WELDOMAT-01'
        )
        """
    )

    op.alter_column(
        "machine_events",
        "machine_id",
        nullable=False,
    )

    op.create_index(
        "ix_machine_events_machine_id",
        "machine_events",
        ["machine_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_machine_events_machine_id",
        "machine_events",
        "machines",
        ["machine_id"],
        ["id"],
    )

    # ---------------------------------------------------------
    # Shift performance
    # ---------------------------------------------------------

    op.add_column(
        "shift_performance",
        sa.Column(
            "machine_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE shift_performance
        SET machine_id = (
            SELECT id
            FROM machines
            WHERE machine_code = 'WELDOMAT-01'
        )
        """
    )

    op.alter_column(
        "shift_performance",
        "machine_id",
        nullable=False,
    )

    op.drop_constraint(
        "uq_shift_date_name",
        "shift_performance",
        type_="unique",
    )

    op.create_index(
        "ix_shift_performance_machine_id",
        "shift_performance",
        ["machine_id"],
        unique=False,
    )

    op.create_unique_constraint(
        "uq_machine_shift_date_name",
        "shift_performance",
        [
            "machine_id",
            "shift_date",
            "shift_name",
        ],
    )

    op.create_foreign_key(
        "fk_shift_performance_machine_id",
        "shift_performance",
        "machines",
        ["machine_id"],
        ["id"],
    )

    # ---------------------------------------------------------
    # Shift configuration
    # ---------------------------------------------------------

    op.create_table(
        "shift_config",
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
            "shift_name",
            sa.String(length=1),
            nullable=False,
        ),
        sa.Column(
            "start_time",
            sa.Time(),
            nullable=False,
        ),
        sa.Column(
            "end_time",
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
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "machine_id",
            "shift_name",
            name="uq_machine_shift_config",
        ),
    )

    op.create_index(
        "ix_shift_config_machine_id",
        "shift_config",
        ["machine_id"],
        unique=False,
    )

    # Default Weldomat shifts.
    op.execute(
        """
        INSERT INTO shift_config (
            machine_id,
            shift_name,
            start_time,
            end_time
        )
        SELECT
            id,
            'A',
            TIME '06:00',
            TIME '14:00'
        FROM machines
        WHERE machine_code = 'WELDOMAT-01'
        """
    )

    op.execute(
        """
        INSERT INTO shift_config (
            machine_id,
            shift_name,
            start_time,
            end_time
        )
        SELECT
            id,
            'B',
            TIME '14:00',
            TIME '20:00'
        FROM machines
        WHERE machine_code = 'WELDOMAT-01'
        """
    )

    op.execute(
        """
        INSERT INTO shift_config (
            machine_id,
            shift_name,
            start_time,
            end_time
        )
        SELECT
            id,
            'C',
            TIME '20:00',
            TIME '06:00'
        FROM machines
        WHERE machine_code = 'WELDOMAT-01'
        """
    )

    # ---------------------------------------------------------
    # Monitor assignments
    # ---------------------------------------------------------

    op.create_table(
        "monitor_assignments",
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
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "unassigned_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["machine_id"],
            ["machines.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_monitor_assignments_machine_id",
        "monitor_assignments",
        ["machine_id"],
        unique=False,
    )

    # ---------------------------------------------------------
    # Heartbeat
    # ---------------------------------------------------------

    op.add_column(
        "monitor_heartbeat",
        sa.Column(
            "machine_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE monitor_heartbeat
        SET machine_id = (
            SELECT id
            FROM machines
            WHERE machine_code = 'WELDOMAT-01'
        )
        """
    )

    op.create_index(
        "ix_monitor_heartbeat_machine_id",
        "monitor_heartbeat",
        ["machine_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_monitor_heartbeat_machine_id",
        "monitor_heartbeat",
        "machines",
        ["machine_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_monitor_heartbeat_machine_id",
        "monitor_heartbeat",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_monitor_heartbeat_machine_id",
        table_name="monitor_heartbeat",
    )
    op.drop_column(
        "monitor_heartbeat",
        "machine_id",
    )

    op.drop_index(
        "ix_monitor_assignments_machine_id",
        table_name="monitor_assignments",
    )
    op.drop_table("monitor_assignments")

    op.drop_index(
        "ix_shift_config_machine_id",
        table_name="shift_config",
    )
    op.drop_table("shift_config")

    op.drop_constraint(
        "fk_shift_performance_machine_id",
        "shift_performance",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_machine_shift_date_name",
        "shift_performance",
        type_="unique",
    )
    op.drop_index(
        "ix_shift_performance_machine_id",
        table_name="shift_performance",
    )

    op.create_unique_constraint(
        "uq_shift_date_name",
        "shift_performance",
        ["shift_date", "shift_name"],
    )

    op.drop_column(
        "shift_performance",
        "machine_id",
    )

    op.drop_constraint(
        "fk_machine_events_machine_id",
        "machine_events",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_machine_events_machine_id",
        table_name="machine_events",
    )
    op.drop_column(
        "machine_events",
        "machine_id",
    )

    op.drop_index(
        "ix_machines_machine_code",
        table_name="machines",
    )
    op.drop_table("machines")