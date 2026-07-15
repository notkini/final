from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "machine_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("state", sa.String(4), nullable=False),
        sa.Column("event_key", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "event_time",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(20),
            nullable=False,
            server_default="gpio",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "state IN ('UP', 'DOWN')",
            name="ck_machine_events_state",
        ),
    )
    op.create_index(
        "ix_machine_events_event_time",
        "machine_events",
        ["event_time"],
    )

    op.create_table(
        "shift_performance",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("shift_date", sa.DateTime(timezone=False), nullable=False),
        sa.Column("shift_name", sa.String(1), nullable=False),
        sa.Column(
            "up_seconds",
            sa.Float,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "down_seconds",
            sa.Float,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "efficiency_pct",
            sa.Float,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "is_final",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "shift_date",
            "shift_name",
            name="uq_shift_date_name",
        ),
        sa.CheckConstraint(
            "up_seconds >= 0",
            name="ck_up_seconds_nonnegative",
        ),
        sa.CheckConstraint(
            "down_seconds >= 0",
            name="ck_down_seconds_nonnegative",
        ),
        sa.CheckConstraint(
            "efficiency_pct BETWEEN 0 AND 100",
            name="ck_efficiency_pct_range",
        ),
    )
    op.create_index(
        "ix_shift_performance_shift_date",
        "shift_performance",
        ["shift_date"],
    )

    op.create_table(
        "monitor_heartbeat",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "last_beat",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("current_state", sa.String(4), nullable=True),
        sa.CheckConstraint(
            "current_state IN ('UP', 'DOWN') OR current_state IS NULL",
            name="ck_heartbeat_current_state",
        ),
    )


def downgrade() -> None:
    op.drop_table("monitor_heartbeat")
    op.drop_index(
        "ix_shift_performance_shift_date",
        table_name="shift_performance",
    )
    op.drop_table("shift_performance")
    op.drop_index(
        "ix_machine_events_event_time",
        table_name="machine_events",
    )
    op.drop_table("machine_events")