"""
Data-adapter layer (Part 3b): translates the real database schema's
ORM shape (see schema_stubs.py -- offline stand-ins for Part 3b,
replaced by real SQLAlchemy query results in Part 3c with no logic
change needed) into lockwood's Train / YardLayout dataclasses that
the solver actually consumes.

This resolves gap #2 (job card severity -- multiple job cards per
train, pick the worst open one), #4 (branding contracts -- map the
active contract's hours onto the flat fields the solver expects),
and #5 (train ID format -- turns out to need no translation at all,
"T01"-"T25" passes straight through as a plain string) from the
Part 3 project context summary. Gap #1 (multi-line yard) and #3
(job card severity's HARD-constraint half) were resolved in Part 3a.
Gap #6 (mileage) was already a non-issue.
"""

from datetime import date, timedelta, datetime

from src.adapters.schema_stubs import DBTrain, DBYardBay
from src.constants import PLANNING_DATE
from src.models import Train, YardLayout, YardLine

_SEVERITY_RANK = {"critical": 3, "major": 2, "minor": 1}

# Fail-safe sentinels for missing data -- see adapt_train() docstring
# for why each of these choices was made. Both are deliberately
# extreme so missing data is NEVER silently treated as "fine".
_NO_CERT_ON_FILE_EXPIRY = PLANNING_DATE - timedelta(days=1)  # treated as already expired
_NEVER_CLEANED_SENTINEL = date.min                            # treated as maximally overdue


def _worst_open_job_card_severity(db_train: DBTrain):
    """
    Among this train's OPEN job cards, returns the most severe
    severity string in lockwood's lowercase format ("critical",
    "major", "minor"), or None if there are no open job cards.

    A train can have multiple open job cards in the real schema
    (unlike lockwood's Part 3a single job_card_severity field, which
    assumes at most one matters); this picks the worst one, since
    that's the one that should drive scheduling.
    """
    open_cards = [jc for jc in db_train.job_cards if str(getattr(jc.status, "value", jc.status)).lower() == "open"]
    if not open_cards:
        return None
    worst = max(open_cards, key=lambda jc: _SEVERITY_RANK[str(getattr(jc.severity, "value", jc.severity)).lower()])
    return str(getattr(worst.severity, "value", worst.severity)).lower()

def _most_recent_cleaning_date(db_train: DBTrain) -> date:
    """
    Returns the most recent COMPLETED cleaning_slots[i].completed_at,
    or the "never cleaned" sentinel if this train has no completed
    cleaning history at all.
    """
    completed_slots = [s for s in db_train.cleaning_slots if s.completed and s.completed_at is not None]
    if not completed_slots:
        return _NEVER_CLEANED_SENTINEL
    val = max(slot.completed_at for slot in completed_slots)
    if isinstance(val, datetime):
        return val.date()
    return val


def _active_branding_contract(db_train: DBTrain):
    """Returns this train's active BrandingContract, or None if it has none."""
    for contract in db_train.branding_contracts:
        if contract.is_active:
            return contract
    return None


def adapt_train(db_train: DBTrain) -> Train:
    if db_train.latest_fitness_cert is not None:
        fitness_cert_expiry = db_train.latest_fitness_cert.expiry_date
        if isinstance(fitness_cert_expiry, datetime):
            fitness_cert_expiry = fitness_cert_expiry.date()
    else:
        fitness_cert_expiry = _NO_CERT_ON_FILE_EXPIRY

    contract = _active_branding_contract(db_train)
    # Round to nearest integer -- the DB stores hours as floats (e.g.
    # 8.64 hours); lockwood's Train dataclass declares these as int,
    # and CP-SAT penalty expressions require integer coefficients.
    # round() rather than int() to avoid systematic under-counting.
    branding_target_hours = round(contract.hours_target) if contract else 0
    branding_hours_this_month = round(contract.hours_delivered) if contract else 0
    # mileage_km is also a float in the DB -- int() is correct here
    # (the wear-leveling penalty uses deviation // 1000, so sub-km
    # precision is irrelevant; truncate rather than round).
    mileage_total = int(db_train.mileage_km)

    return Train(
        train_id=db_train.train_id,
        fitness_cert_expiry=fitness_cert_expiry,
        job_card_severity=_worst_open_job_card_severity(db_train),
        last_cleaned=_most_recent_cleaning_date(db_train),
        branding_hours_this_month=branding_hours_this_month,
        branding_target_hours=branding_target_hours,
        current_bay=db_train.current_bay_id,
        mileage_total=mileage_total,
    )


def adapt_yard_layout(db_bays: list) -> YardLayout:
    """
    Translates a flat list of real-schema DBYardBay rows into
    lockwood's multi-line YardLayout.

    DESIGN DECISION: only bay_type == "STABLING" bays are included.
    The Part 3 project context summary's gap #1 discussion is
    specifically about the 5 STABLING lines -- the maintenance track
    and wash track are physically single-purpose spurs a train enters
    directly for servicing, not a queue trains get blocked behind the
    way a stabling line is, so the front/deep blocking rule this
    YardLayout exists to support does not apply to them. If that
    assumption turns out to be wrong once the real yard graph
    (Neo4j, app/services/yard_graph.py) is consulted in Part 3c,
    this filter is the one line to revisit.

    Args:
        db_bays: flat list of DBYardBay objects, any order, any mix
            of bay_type values (only STABLING ones are used).

    Returns:
        A lockwood YardLayout, with one YardLine per distinct line_id
        among the STABLING bays, each bay_order sorted by `position`
        ascending (1 = entrance/exit end first).
    """
    # NOTE (Part 3c correction): real BayType values are lowercase
    # ("stabling", not "STABLING") -- confirmed by reading
    # app/models/yard.py directly. str(...).lower() is safe whether
    # bay_type is a plain string or a str-Enum member.
    stabling_bays = [b for b in db_bays if str(getattr(b.bay_type, "value", b.bay_type)).lower() == "stabling"]

    bays_by_line = {}
    for bay in stabling_bays:
        bays_by_line.setdefault(bay.line_id, []).append(bay)

    lines = {}
    for line_id, bays in bays_by_line.items():
        bays_sorted = sorted(bays, key=lambda b: b.position)
        lines[line_id] = YardLine(
            line_id=line_id,
            bay_order=[b.bay_id for b in bays_sorted],
        )

    return YardLayout(lines=lines)
