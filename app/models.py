from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func


Base = declarative_base()


class Machine(Base):
    __tablename__ = "machines"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    machine_name = Column(
        String(100),
        nullable=False,
    )

    machine_code = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class MachineEvent(Base):
    __tablename__ = "machine_events"

    __table_args__ = (
        CheckConstraint(
            "state IN ('UP', 'DOWN')",
            name="ck_machine_events_state",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    machine_id = Column(
        Integer,
        ForeignKey("machines.id"),
        nullable=False,
        index=True,
    )

    state = Column(
        String(4),
        nullable=False,
    )

    event_time = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    source = Column(
        String(20),
        nullable=False,
        default="gpio",
    )

    event_key = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    machine = relationship("Machine")


class ShiftConfig(Base):
    __tablename__ = "shift_config"

    __table_args__ = (
        UniqueConstraint(
            "machine_id",
            "shift_name",
            name="uq_machine_shift_config",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    machine_id = Column(
        Integer,
        ForeignKey("machines.id"),
        nullable=False,
        index=True,
    )

    shift_name = Column(
        String(1),
        nullable=False,
    )

    start_time = Column(
        Time,
        nullable=False,
    )

    end_time = Column(
        Time,
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    machine = relationship("Machine")


class MealConfig(Base):
    __tablename__ = "meal_config"

    __table_args__ = (
        UniqueConstraint(
            "machine_id",
            "meal_name",
            name="uq_machine_meal_name",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    machine_id = Column(
        Integer,
        ForeignKey("machines.id"),
        nullable=False,
        index=True,
    )

    meal_name = Column(
        String(20),
        nullable=False,
    )

    start_time = Column(
        Time,
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    machine = relationship("Machine")


class ShiftPerformance(Base):
    __tablename__ = "shift_performance"

    __table_args__ = (
        UniqueConstraint(
            "machine_id",
            "shift_date",
            "shift_name",
            name="uq_machine_shift_date_name",
        ),
        CheckConstraint(
            "up_seconds >= 0",
            name="ck_up_seconds_nonnegative",
        ),
        CheckConstraint(
            "down_seconds >= 0",
            name="ck_down_seconds_nonnegative",
        ),
        CheckConstraint(
            "efficiency_pct BETWEEN 0 AND 100",
            name="ck_efficiency_pct_range",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    machine_id = Column(
        Integer,
        ForeignKey("machines.id"),
        nullable=False,
        index=True,
    )

    shift_date = Column(
        DateTime(timezone=False),
        nullable=False,
        index=True,
    )

    shift_name = Column(
        String(1),
        nullable=False,
    )

    up_seconds = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    down_seconds = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    efficiency_pct = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    is_final = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    last_updated = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    machine = relationship("Machine")


class MonitorAssignment(Base):
    __tablename__ = "monitor_assignments"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    machine_id = Column(
        Integer,
        ForeignKey("machines.id"),
        nullable=False,
        index=True,
    )

    assigned_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    unassigned_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    machine = relationship("Machine")


class MonitorHeartbeat(Base):
    __tablename__ = "monitor_heartbeat"

    __table_args__ = (
        CheckConstraint(
            "current_state IN ('UP', 'DOWN') "
            "OR current_state IS NULL",
            name="ck_heartbeat_current_state",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        default=1,
    )

    machine_id = Column(
        Integer,
        ForeignKey("machines.id"),
        nullable=True,
        index=True,
    )

    last_beat = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    current_state = Column(
        String(4),
        nullable=True,
    )

    machine = relationship("Machine")