"""
Explainability service â€” translates CP-SAT solver constraint reasoning into
plain-English explanations for the dashboard and natural language query feature.

This service powers the GET /plan/{plan_id}/explain/{train_id} endpoint.

Key responsibilities:
  1. Take solver output (assignment state + constraint metadata)
  2. Query train's actual data (certs, job cards, cleaning, branding, yard position)
  3. Generate human-readable explanation with specific details
  4. Return list of constraints that were considered in the decision

Use cases:
  - Dashboard tooltip on hover over a train assignment
  - Natural language query: "Why is train 9 in maintenance?"
  - Audit trail: understand why the AI made specific decisions
"""

from datetime import date
from typing import List, Dict, Optional
import logging

from sqlalchemy.orm import Session

import re

from app.models.train import Train, JobCard, JobCardStatus, JobCardSeverity
from app.models.plan import PlanAssignment, AssignmentState, ConstraintType
import os
import sys
from pathlib import Path

# Add LOCKWOOD to sys.path: supports LOCKWOOD_PATH env var or dynamic workspace search
lockwood_dir = os.getenv("LOCKWOOD_PATH")
if not lockwood_dir:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "LOCKWOOD"
        if candidate.exists() and (candidate / "src").exists():
            lockwood_dir = str(candidate)
            break
if not lockwood_dir:
    lockwood_dir = str(Path(__file__).resolve().parents[3] / "LOCKWOOD")

if lockwood_dir not in sys.path:
    sys.path.insert(0, lockwood_dir)

from src.adapters.db_adapter import adapt_train, adapt_yard_layout
from src.solver.decision_breakdown import explain_decision
from src.solver.nl_query import answer_query as lockwood_answer_query

logger = logging.getLogger(__name__)


class ExplainabilityEngine:
    """
    Translates solver constraint reasoning into natural language.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # -----------------------------------------------------------------------
    # Main explanation generation
    # -----------------------------------------------------------------------
    
    def explain_assignment(
        self,
        train_id: str,
        assignment: PlanAssignment,
    ) -> Dict:
        """
        Generate a complete explanation for a train's assignment.
        
        Returns:
          {
            "train_id": "T09",
            "assigned_state": "maintenance",
            "explanation": "Plain English multi-sentence explanation...",
            "constraints_considered": ["fitness_cert", "job_cards", ...],
            "constraint_details": {...}  # structured data for drill-down
          }
        """
        
        # Fetch train with all related data
        train = self.db.query(Train).filter(Train.train_id == train_id).first()
        if not train:
            return {
                "train_id": train_id,
                "assigned_state": "unknown",
                "explanation": f"Train {train_id} not found in database.",
                "constraints_considered": [],
            }
        
        # Part 4c: real quantitative breakdown, additive -- None if it
        # couldn't be computed (see _get_quantitative_breakdown docstring).
        # Computed BEFORE the state-dispatch so it can be passed into
        # _explain_service_assignment for the wear-leveling fix.
        quantitative_breakdown = self._get_quantitative_breakdown(train_id, assignment.plan)

        # Build explanation based on assignment state
        if assignment.state == AssignmentState.MAINTENANCE:
            explanation = self._explain_maintenance_assignment(train, assignment)
        elif assignment.state == AssignmentState.SERVICE:
            explanation = self._explain_service_assignment(train, assignment, quantitative_breakdown)
        elif assignment.state == AssignmentState.CLEANING:
            explanation = self._explain_cleaning_assignment(train, assignment)
        elif assignment.state == AssignmentState.STANDBY:
            explanation = self._explain_standby_assignment(train, assignment)
        elif assignment.state == AssignmentState.BREAKDOWN:
            explanation = self._explain_breakdown_assignment(train, assignment)
        else:
            explanation = f"Train {train_id} assigned to {assignment.state.value}."
        
        # Extract constraint details for structured drill-down
        constraint_details = self._extract_constraint_details(train)

        return {
            "train_id": train_id,
            "assigned_state": assignment.state.value,
            "explanation": explanation,
            "constraints_considered": assignment.constraints_considered.split(",") if assignment.constraints_considered else [],
            "constraint_type": assignment.constraint_type.value,
            "constraint_details": constraint_details,
            "quantitative_breakdown": quantitative_breakdown,
        }
    
    # -----------------------------------------------------------------------
    # State-specific explanation builders
    # -----------------------------------------------------------------------
    
    def _explain_maintenance_assignment(self, train: Train, assignment: PlanAssignment) -> str:
        """Generate explanation for maintenance assignment."""
        
        reasons = []
        
        # Check for critical job cards (hard constraint)
        critical_jobs = [
            jc for jc in train.job_cards
            if jc.status == JobCardStatus.OPEN and jc.severity == JobCardSeverity.CRITICAL
        ]
        if critical_jobs:
            job_refs = ", ".join(jc.jc_ref for jc in critical_jobs)
            reasons.append(
                f"Train {train.train_id} has {len(critical_jobs)} open critical job card(s) "
                f"({job_refs}) which legally prohibit service assignment. This is a hard constraint "
                f"that cannot be overridden."
            )
        
        # Check fitness cert expiry (hard if expired, soft if expiring soon)
        cert = train.latest_fitness_cert
        if cert:
            if cert.is_expired:
                reasons.append(
                    f"The fitness certificate ({cert.cert_ref}) expired {abs(cert.days_to_expiry)} days ago, "
                    f"making the train unfit for passenger service (hard constraint)."
                )
            elif cert.is_expiring_soon:
                reasons.append(
                    f"The fitness certificate ({cert.cert_ref}) expires in {cert.days_to_expiry} days, "
                    f"creating a soft constraint preference for maintenance to renew the cert before it lapses."
                )
        
        # Check major job cards (soft constraint)
        major_jobs = [
            jc for jc in train.job_cards
            if jc.status == JobCardStatus.OPEN and jc.severity == JobCardSeverity.MAJOR
        ]
        if major_jobs:
            reasons.append(
                f"Additionally, {len(major_jobs)} major job card(s) are open, "
                f"creating a soft constraint to address these issues."
            )
        
        # Fallback if no specific reason found
        if not reasons:
            reasons.append(
                f"Train {train.train_id} is scheduled for routine maintenance based on "
                f"operational planning priorities."
            )
        
        return " ".join(reasons)
    
    def _explain_service_assignment(self, train: Train, assignment: PlanAssignment, breakdown: Optional[Dict] = None) -> str:
        """Generate explanation for service assignment."""
        
        parts = [f"Train {train.train_id} is assigned to passenger service."]
        
        # Positive factors (why service is suitable)
        cert = train.latest_fitness_cert
        if cert and not cert.is_expired and not cert.is_expiring_soon:
            parts.append(
                f"Fitness certificate ({cert.cert_ref}) is valid until "
                f"{cert.expiry_date.isoformat()} ({cert.days_to_expiry} days remaining)."
            )
        
        open_job_cards = [jc for jc in train.job_cards if jc.status == JobCardStatus.OPEN]
        if not open_job_cards:
            parts.append("No open job cards.")
        elif all(jc.severity == JobCardSeverity.MINOR for jc in open_job_cards):
            parts.append(
                f"{len(open_job_cards)} minor job card(s) open, "
                f"but none block service assignment."
            )
        
        # Branding contract preference (soft constraint)
        active_branding = [bc for bc in train.branding_contracts if bc.is_active]
        if active_branding:
            bc = active_branding[0]
            if bc.is_under_target:
                parts.append(
                    f"Branding contract ({bc.contract_ref} with {bc.advertiser}) has delivered "
                    f"{bc.hours_delivered:.1f} of {bc.hours_target:.1f} target hours, "
                    f"creating a soft constraint preference for service assignment to meet contractual obligations."
                )
        
        # Mileage wear-leveling (soft constraint) -- Part 4c: this now
        # actually does the fleet-average comparison the old code's
        # comment said it would, using the real penalty value when
        # available rather than just restating the train's own mileage.
        if breakdown is not None:
            wear_penalty = breakdown["chosen_state_penalty_breakdown"]["wear_leveling"]
            fleet_avg = breakdown.get("fleet_average_mileage_km")
            if fleet_avg is not None:
                comparison = "above" if train.mileage_km > fleet_avg else "at or below"
                parts.append(
                    f"Cumulative mileage: {train.mileage_km:,.0f} km, "
                    f"{comparison} the fleet average of {fleet_avg:,.0f} km "
                    f"(wear-leveling penalty: {wear_penalty})."
                )
            else:
                parts.append(
                    f"Cumulative mileage: {train.mileage_km:,.0f} km "
                    f"(wear-leveling penalty for this assignment: {wear_penalty})."
                )
        else:
            parts.append(
                f"Cumulative mileage: {train.mileage_km:,.0f} km "
                f"(considered for wear-leveling across the fleet)."
            )
        
        return " ".join(parts)
    
    def _explain_cleaning_assignment(self, train: Train, assignment: PlanAssignment) -> str:
        """Generate explanation for cleaning assignment."""
        
        cleaning_due = [cs for cs in train.cleaning_slots if not cs.completed]
        
        if cleaning_due:
            slot = cleaning_due[0]
            return (
                f"Train {train.train_id} has a scheduled cleaning slot tonight at "
                f"{slot.scheduled_at.strftime('%H:%M')}. This is a soft constraint preference "
                f"to maintain hygiene standards. The train is otherwise available for service."
            )
        
        return (
            f"Train {train.train_id} is assigned to the wash bay for routine cleaning "
            f"based on operational scheduling."
        )
    
    def _explain_standby_assignment(self, train: Train, assignment: PlanAssignment) -> str:
        """Generate explanation for standby/reserve assignment."""
        
        return (
            f"Train {train.train_id} is held in standby as reserve capacity. "
            f"This train is operationally ready for service and can be deployed if "
            f"peak demand exceeds the planned service allocation or if another train "
            f"experiences an unplanned breakdown. "
            f"Fitness certificate valid, no blocking job cards."
        )
    
    def _explain_breakdown_assignment(self, train: Train, assignment: PlanAssignment) -> str:
        """Generate explanation for breakdown status."""
        
        return (
            f"Train {train.train_id} is marked as breakdown status, indicating an "
            f"unplanned operational failure. This is a hard constraint forcing the train "
            f"out of service until the issue is diagnosed and resolved. "
            f"This train cannot be assigned to any service or scheduled maintenance "
            f"activities until cleared by engineering."
        )
    
    # -----------------------------------------------------------------------
    # Lockwood integration (Part 4c) -- real quantitative explanations
    # -----------------------------------------------------------------------

    def _build_lockwood_context(self, plan):
        """
        Builds (lockwood_trains, yard_layout, plan_list) for a given
        InductionPlan, reusing the same adapters wired in Part 3c.
        Returns (None, None, None) if this plan can't currently support
        a quantitative breakdown (e.g. no assignments yet) -- callers
        must treat that as "degrade gracefully", never as an error to
        propagate to the API response.
        """
        if not plan or not plan.assignments:
            return None, None, None

        db_trains = self.db.query(Train).all()
        db_bays = self.db.query(YardBay).all()
        lockwood_trains = [adapt_train(t) for t in db_trains]
        yard_layout = adapt_yard_layout(db_bays)
        plan_list = [
            {"train_id": a.train_id, "assigned_state": a.state.value}
            for a in plan.assignments
        ]
        return lockwood_trains, yard_layout, plan_list

    def _get_quantitative_breakdown(self, train_id: str, plan) -> Optional[Dict]:
        """
        Returns explain_decision()'s real penalty breakdown for this
        train in this plan, or None if it can't be computed. Never
        raises -- any failure here must degrade the explanation to
        prose-only, not break the endpoint.
        """
        try:
            lockwood_trains, yard_layout, plan_list = self._build_lockwood_context(plan)
            if lockwood_trains is None:
                return None
            return explain_decision(train_id, plan_list, lockwood_trains, yard_layout)
        except Exception as exc:
            logger.warning(f"Could not compute quantitative breakdown for {train_id}: {exc}")
            return None

    def _normalize_train_references(self, query: str, all_trains: list) -> str:
        """
        Rewrites casual train references ("train 9", "train t9") into
        the exact zero-padded ID format ("train T09") that lockwood's
        answer_query() can resolve via exact case-insensitive match.
        Leaves anything it can't confidently resolve untouched, so
        answer_query() falls through to its own fallback message
        rather than this function guessing wrong.
        """
        known_ids = {t.train_id.upper() for t in all_trains}

        def _replace(match):
            num = match.group(1).lower().lstrip("t")
            candidate = f"T{int(num):02d}"
            if candidate in known_ids:
                return f"train {candidate}"
            return match.group(0)

        return re.sub(r"train\s+(t?\d+)", _replace, query, flags=re.IGNORECASE)

    # -----------------------------------------------------------------------
    # Constraint detail extraction (structured data for drill-down)
    # -----------------------------------------------------------------------
    
    def _extract_constraint_details(self, train: Train) -> Dict:
        """
        Extract structured constraint data for detailed drill-down in the UI.
        
        Returns a dict with all constraint-relevant data in a structured format.
        """
        cert = train.latest_fitness_cert
        
        return {
            "fitness_cert": {
                "cert_ref": cert.cert_ref if cert else None,
                "expiry_date": cert.expiry_date.isoformat() if cert else None,
                "days_to_expiry": cert.days_to_expiry if cert else None,
                "is_expired": cert.is_expired if cert else None,
                "is_expiring_soon": cert.is_expiring_soon if cert else None,
                "status": "expired" if (cert and cert.is_expired) else (
                    "expiring_soon" if (cert and cert.is_expiring_soon) else "valid"
                ),
            },
            "job_cards": [
                {
                    "jc_ref": jc.jc_ref,
                    "status": jc.status.value,
                    "severity": jc.severity.value,
                    "description": jc.description,
                }
                for jc in train.job_cards if jc.status == JobCardStatus.OPEN
            ],
            "cleaning": {
                "slots_due": len([cs for cs in train.cleaning_slots if not cs.completed]),
                "next_scheduled": (
                    train.cleaning_slots[0].scheduled_at.isoformat()
                    if train.cleaning_slots and not train.cleaning_slots[0].completed
                    else None
                ),
            },
            "branding": [
                {
                    "contract_ref": bc.contract_ref,
                    "advertiser": bc.advertiser,
                    "hours_target": bc.hours_target,
                    "hours_delivered": bc.hours_delivered,
                    "hours_remaining": bc.hours_remaining,
                    "is_under_target": bc.is_under_target,
                }
                for bc in train.branding_contracts if bc.is_active
            ],
            "yard": {
                "current_bay": train.current_bay_id,
                "bay_type": train.current_bay.bay_type.value if train.current_bay else None,
            },
            "mileage_km": train.mileage_km,
        }
    
    # -----------------------------------------------------------------------
    # Batch explanation (for full plan summary)
    # -----------------------------------------------------------------------
    
    def explain_full_plan(self, plan_id: str) -> List[Dict]:
        """
        Generate explanations for all assignments in a plan.
        
        Returns a list of explanation dicts, one per train.
        Useful for dashboard summary view.
        """
        from app.models.plan import InductionPlan
        
        plan = self.db.query(InductionPlan).filter(InductionPlan.plan_id == plan_id).first()
        if not plan:
            return []
        
        explanations = []
        for assignment in plan.assignments:
            explanation = self.explain_assignment(assignment.train_id, assignment)
            explanations.append(explanation)
        
        return explanations
    
    # -----------------------------------------------------------------------
    # Natural language query support
    # -----------------------------------------------------------------------
    
    def answer_natural_query(self, query: str, plan_id: str) -> Optional[Dict]:
        """
        Answer natural language questions about plan assignments.

        Part 4c: delegates to lockwood's answer_query() (Part 4b),
        which understands five question shapes grounded in real
        penalty numbers -- strictly more capable than the DB-query
        pattern-matching this replaces. The only adaptation needed is
        train-ID-format normalization (see _normalize_train_references).
        """
        from app.models.plan import InductionPlan

        plan = self.db.query(InductionPlan).filter(InductionPlan.plan_id == plan_id).first()
        lockwood_trains, yard_layout, plan_list = self._build_lockwood_context(plan)

        if lockwood_trains is None:
            return {
                "query": query,
                "answer": "I couldn't parse that question, or there's no completed plan yet to answer "
                          "questions about. Try asking 'Why is train 9 in maintenance?' or "
                          "'Which trains have critical job cards?'",
            }

        normalized_query = self._normalize_train_references(query, lockwood_trains)
        return lockwood_answer_query(normalized_query, plan_list, lockwood_trains, yard_layout)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def get_explainability_engine(db: Session) -> ExplainabilityEngine:
    """Return an explainability engine instance."""
    return ExplainabilityEngine(db)
