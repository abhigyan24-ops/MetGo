"""Initial schema — all KMRL tables

Revision ID: 001
Revises:
Create Date: 2026-08-14

Creates:
  stations, trains, fitness_certs, job_cards, cleaning_slots,
  branding_contracts, yard_lines, yard_bays,
  induction_plans, plan_assignments, shunt_moves,
  mileage_snapshots, cert_events
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # stations
    # ------------------------------------------------------------------
    op.create_table(
        "stations",
        sa.Column("stop_id",                  sa.String(20),  primary_key=True),
        sa.Column("stop_name",                sa.String(100), nullable=False),
        sa.Column("latitude",                 sa.Float(),     nullable=False),
        sa.Column("longitude",                sa.Float(),     nullable=False),
        sa.Column("sequence",                 sa.Integer(),   nullable=False),
        sa.Column("is_interchange",           sa.Boolean(),   default=False),
        sa.Column("distance_from_aluva_km",   sa.Float(),     nullable=True),
    )

    # ------------------------------------------------------------------
    # yard_lines
    # ------------------------------------------------------------------
    op.create_table(
        "yard_lines",
        sa.Column("line_id",   sa.String(10), primary_key=True),
        sa.Column("line_name", sa.String(50), nullable=False),
        sa.Column("bay_count", sa.Integer(),  nullable=False),
        sa.Column("line_type", sa.String(20), nullable=False, server_default="stabling"),
    )

    # ------------------------------------------------------------------
    # yard_bays
    # ------------------------------------------------------------------
    op.create_table(
        "yard_bays",
        sa.Column("bay_id",      sa.String(10), primary_key=True),
        sa.Column("line_id",     sa.String(10), sa.ForeignKey("yard_lines.line_id"), nullable=False),
        sa.Column("position",    sa.Integer(),  nullable=False),
        sa.Column("bay_type",    sa.String(20), nullable=False, server_default="stabling"),
        sa.Column("is_active",   sa.Boolean(),  default=True),
        sa.Column("occupied_by", sa.String(10), nullable=True),
        sa.Column("updated_at",  sa.DateTime(timezone=True), nullable=True),
    )

    # ------------------------------------------------------------------
    # trains
    # ------------------------------------------------------------------
    op.create_table(
        "trains",
        sa.Column("train_id",      sa.String(10),  primary_key=True),
        sa.Column("coach_count",   sa.Integer(),   nullable=False, server_default="3"),
        sa.Column("current_bay_id",sa.String(10),  sa.ForeignKey("yard_bays.bay_id"), nullable=True),
        sa.Column("mileage_km",    sa.Float(),     nullable=False, server_default="0"),
        sa.Column("status",        sa.String(20),  nullable=False, server_default="available"),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",    sa.DateTime(timezone=True), nullable=True),
    )

    # Now add the FK from yard_bays.occupied_by → trains.train_id
    op.create_foreign_key(
        "fk_bay_train", "yard_bays", "trains", ["occupied_by"], ["train_id"]
    )

    # ------------------------------------------------------------------
    # fitness_certs
    # ------------------------------------------------------------------
    op.create_table(
        "fitness_certs",
        sa.Column("id",          sa.Integer(),   primary_key=True, autoincrement=True),
        sa.Column("train_id",    sa.String(10),  sa.ForeignKey("trains.train_id"), nullable=False),
        sa.Column("cert_ref",    sa.String(30),  nullable=False),
        sa.Column("issued_date", sa.Date(),      nullable=False),
        sa.Column("expiry_date", sa.Date(),      nullable=False),
        sa.Column("is_active",   sa.Boolean(),   default=True),
    )
    op.create_index("ix_fitness_certs_train_id", "fitness_certs", ["train_id"])

    # ------------------------------------------------------------------
    # job_cards
    # ------------------------------------------------------------------
    op.create_table(
        "job_cards",
        sa.Column("id",          sa.Integer(),   primary_key=True, autoincrement=True),
        sa.Column("jc_ref",      sa.String(20),  nullable=False, unique=True),
        sa.Column("train_id",    sa.String(10),  sa.ForeignKey("trains.train_id"), nullable=False),
        sa.Column("description", sa.Text(),      nullable=False),
        sa.Column("status",      sa.String(20),  nullable=False, server_default="open"),
        sa.Column("severity",    sa.String(20),  nullable=False, server_default="minor"),
        sa.Column("raised_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("closed_at",   sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_job_cards_train_id", "job_cards", ["train_id"])

    # ------------------------------------------------------------------
    # cleaning_slots
    # ------------------------------------------------------------------
    op.create_table(
        "cleaning_slots",
        sa.Column("id",           sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column("train_id",     sa.String(10), sa.ForeignKey("trains.train_id"), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed",    sa.Boolean(),  default=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes",        sa.Text(),     nullable=True),
    )
    op.create_index("ix_cleaning_slots_train_id", "cleaning_slots", ["train_id"])

    # ------------------------------------------------------------------
    # branding_contracts
    # ------------------------------------------------------------------
    op.create_table(
        "branding_contracts",
        sa.Column("id",              sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column("train_id",        sa.String(10), sa.ForeignKey("trains.train_id"), nullable=False),
        sa.Column("contract_ref",    sa.String(30), nullable=False),
        sa.Column("advertiser",      sa.String(100),nullable=True),
        sa.Column("start_date",      sa.Date(),     nullable=False),
        sa.Column("end_date",        sa.Date(),     nullable=False),
        sa.Column("hours_target",    sa.Float(),    nullable=False, server_default="0"),
        sa.Column("hours_delivered", sa.Float(),    nullable=False, server_default="0"),
        sa.Column("is_active",       sa.Boolean(),  default=True),
    )
    op.create_index("ix_branding_contracts_train_id", "branding_contracts", ["train_id"])

    # ------------------------------------------------------------------
    # induction_plans
    # ------------------------------------------------------------------
    op.create_table(
        "induction_plans",
        sa.Column("plan_id",            sa.String(40),  primary_key=True),
        sa.Column("plan_date",          sa.Date(),      nullable=False),
        sa.Column("generated_at",       sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status",             sa.String(20),  nullable=False, server_default="pending"),
        sa.Column("celery_task_id",     sa.String(60),  nullable=True),
        sa.Column("is_what_if",         sa.Boolean(),   default=False),
        sa.Column("solver_duration_ms", sa.Integer(),   nullable=True),
        sa.Column("solver_status",      sa.String(30),  nullable=True),
    )

    # ------------------------------------------------------------------
    # plan_assignments
    # ------------------------------------------------------------------
    op.create_table(
        "plan_assignments",
        sa.Column("id",                     sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column("plan_id",                sa.String(40), sa.ForeignKey("induction_plans.plan_id"), nullable=False),
        sa.Column("train_id",               sa.String(10), sa.ForeignKey("trains.train_id"),         nullable=False),
        sa.Column("state",                  sa.String(20), nullable=False),
        sa.Column("reason",                 sa.Text(),     nullable=False),
        sa.Column("constraint_type",        sa.String(10), nullable=False),
        sa.Column("constraints_considered", sa.String(200), nullable=True),
    )
    op.create_index("ix_plan_assignments_plan_id",  "plan_assignments", ["plan_id"])
    op.create_index("ix_plan_assignments_train_id", "plan_assignments", ["train_id"])

    # ------------------------------------------------------------------
    # shunt_moves
    # ------------------------------------------------------------------
    op.create_table(
        "shunt_moves",
        sa.Column("id",       sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column("plan_id",  sa.String(40), sa.ForeignKey("induction_plans.plan_id"), nullable=False),
        sa.Column("train_id", sa.String(10), sa.ForeignKey("trains.train_id"),         nullable=False),
        sa.Column("from_bay", sa.String(10), nullable=False),
        sa.Column("to_bay",   sa.String(10), nullable=False),
        sa.Column("sequence", sa.Integer(),  nullable=False, server_default="0"),
    )
    op.create_index("ix_shunt_moves_plan_id", "shunt_moves", ["plan_id"])

    # ------------------------------------------------------------------
    # mileage_snapshots  (converted to TimescaleDB hypertable at startup)
    # ------------------------------------------------------------------
    op.create_table(
        "mileage_snapshots",
        sa.Column("id",          sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column("train_id",    sa.String(10), sa.ForeignKey("trains.train_id"), nullable=False),
        sa.Column("mileage_km",  sa.Float(),    nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source",      sa.String(30), server_default="simulated"),
    )
    op.create_index("ix_mileage_snapshots_train_id",    "mileage_snapshots", ["train_id"])
    op.create_index("ix_mileage_snapshots_recorded_at", "mileage_snapshots", ["recorded_at"])

    # ------------------------------------------------------------------
    # cert_events  (converted to TimescaleDB hypertable at startup)
    # ------------------------------------------------------------------
    op.create_table(
        "cert_events",
        sa.Column("id",             sa.Integer(),  primary_key=True, autoincrement=True),
        sa.Column("train_id",       sa.String(10), sa.ForeignKey("trains.train_id"), nullable=False),
        sa.Column("cert_ref",       sa.String(30), nullable=False),
        sa.Column("days_to_expiry", sa.Integer(),  nullable=False),
        sa.Column("event_at",       sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type",     sa.String(30), nullable=False),
        sa.Column("notes",          sa.Text(),     nullable=True),
    )
    op.create_index("ix_cert_events_train_id", "cert_events", ["train_id"])
    op.create_index("ix_cert_events_event_at", "cert_events", ["event_at"])


def downgrade() -> None:
    op.drop_table("cert_events")
    op.drop_table("mileage_snapshots")
    op.drop_table("shunt_moves")
    op.drop_table("plan_assignments")
    op.drop_table("induction_plans")
    op.drop_table("branding_contracts")
    op.drop_table("cleaning_slots")
    op.drop_table("job_cards")
    op.drop_table("fitness_certs")
    op.drop_foreign_key("fk_bay_train", "yard_bays")
    op.drop_table("trains")
    op.drop_table("yard_bays")
    op.drop_table("yard_lines")
    op.drop_table("stations")
