"""
Natural-language query layer over Part 4a's decision-breakdown module.

Answers plain-English questions about an already-solved plan by
formatting explain_decision()'s / evaluate_state_for_train()'s real
numbers into readable sentences -- it does NOT invent any new
reasoning of its own; every number in every answer traces back
directly to a build_*_penalty() call or a hard-constraint check
already verified in Part 4a.

Supported query patterns (case-insensitive, checked in this order):
  1. "why is/was <train> in/assigned <state>?"        -> full breakdown
  2. "why isn't/can't/couldn't <train> be in <state>?" -> single alternative
  3. "which trains are in <state>?"                     -> list by state
  4. "which trains have <severity> job cards?"          -> list by job card severity
  5. "what would happen if <train> were in <state>?"    -> hypothetical, single state
  6. anything else                                      -> fallback message naming
                                                            the patterns this understands

Train IDs are resolved case-insensitively against whatever IDs are
actually in ll_trains (works for lockwood's "KMRL-01" test format
and the real "T01"-"T25" format equally -- no format is hardcoded).
"""

import re

from src.solver.decision_breakdown import evaluate_state_for_train, explain_decision
from src.solver.states import ALL_STATES


def _resolve_train_id(token: str, all_trains: list):
    """
    Matches a token extracted from a query against the real train IDs
    present in ll_trains, case-insensitively. Returns the correctly-
    cased train_id, or None if no train matches.
    """
    token_lower = token.lower()
    for train in all_trains:
        if train.train_id.lower() == token_lower:
            return train.train_id
    return None


def _resolve_state(token: str):
    """Matches a token against ALL_STATES case-insensitively, or returns None."""
    token_lower = token.lower()
    for state in ALL_STATES:
        if state == token_lower:
            return state
    return None


def _format_full_explanation(train_id: str, plan: list, all_trains: list, yard_layout) -> str:
    """
    Turns explain_decision()'s structured output into a readable
    multi-sentence explanation: the chosen state and its cost, then
    each alternative -- infeasible ones with their real reason,
    feasible-but-worse ones with their exact penalty delta.
    """
    result = explain_decision(train_id, plan, all_trains, yard_layout)
    chosen = result["chosen_state"]
    chosen_penalty = result["chosen_state_penalty"]

    breakdown = result["chosen_state_penalty_breakdown"]
    nonzero_parts = [f"{name.replace('_', ' ')}: {value}" for name, value in breakdown.items() if value > 0]
    if nonzero_parts:
        cost_sentence = (
            f"{train_id} is assigned {chosen}, at a soft-constraint cost of "
            f"{chosen_penalty} ({', '.join(nonzero_parts)})."
        )
    else:
        cost_sentence = f"{train_id} is assigned {chosen}, at zero soft-constraint cost -- no penalties apply."

    alt_sentences = []
    for alt_state, alt in sorted(result["alternatives"].items()):
        if alt["feasible"]:
            if alt["penalty_delta"] == 0:
                alt_sentences.append(f"{alt_state} would have cost exactly the same ({alt['penalty_total']}).")
            elif alt["penalty_delta"] > 0:
                alt_sentences.append(
                    f"{alt_state} was legal but would have cost {alt['penalty_delta']} more "
                    f"({alt['penalty_total']} total)."
                )
            else:
                alt_sentences.append(
                    f"{alt_state} was legal and would actually have cost {-alt['penalty_delta']} LESS "
                    f"({alt['penalty_total']} total) -- worth double-checking why it wasn't chosen."
                )
        else:
            alt_sentences.append(f"{alt_state} was not legal: {alt['hard_block_reason']}")

    return cost_sentence + " " + " ".join(alt_sentences)


def _format_single_alternative(train_id: str, candidate_state: str, plan: list, all_trains: list, yard_layout) -> str:
    trains_by_id = {t.train_id: t for t in all_trains}
    train = trains_by_id[train_id]
    plan_by_id = {row["train_id"]: row["assigned_state"] for row in plan}
    chosen_state = plan_by_id[train_id]

    if chosen_state == candidate_state:
        return f"{train_id} IS currently assigned {candidate_state}."

    evaluation = evaluate_state_for_train(train, candidate_state, plan, all_trains, yard_layout)
    if not evaluation["feasible"]:
        return f"{train_id} cannot be assigned {candidate_state}: {evaluation['hard_block_reason']}"

    chosen_eval = evaluate_state_for_train(train, chosen_state, plan, all_trains, yard_layout)
    delta = evaluation["soft_penalty_total"] - chosen_eval["soft_penalty_total"]
    if delta > 0:
        return (
            f"{train_id} COULD legally be assigned {candidate_state} -- it's not hard-blocked -- "
            f"but it would cost {delta} more in soft-constraint penalties than the current "
            f"{chosen_state} assignment ({evaluation['soft_penalty_total']} vs {chosen_eval['soft_penalty_total']})."
        )
    elif delta < 0:
        return (
            f"{train_id} COULD legally be assigned {candidate_state}, and it would actually cost "
            f"{-delta} LESS than the current {chosen_state} assignment -- worth checking why "
            f"the plan didn't choose it."
        )
    else:
        return (
            f"{train_id} COULD legally be assigned {candidate_state} at exactly the same cost "
            f"as the current {chosen_state} assignment ({evaluation['soft_penalty_total']} each)."
        )


def answer_query(query: str, plan: list, all_trains: list, yard_layout) -> dict:
    """
    Parses and answers one natural-language query about an already-
    solved plan.

    Returns:
        {"query": query, "answer": str, "matched_pattern": str | None}
        matched_pattern is None only for the fallback case.
    """
    q = query.strip().lower()
    plan_by_id = {row["train_id"]: row["assigned_state"] for row in plan}

    # Pattern 2 checked BEFORE pattern 1: "why isn't/can't/couldn't X be Y"
    # is a more specific phrasing that would otherwise also match
    # pattern 1's looser "why is/was X in Y" if checked second.
    m = re.search(
        r"why\s+(?:isn'?t|can'?t|couldn'?t)\s+(?:train\s+)?([\w\-]+)\s+(?:be\s+)?(?:in\s+|assigned\s+)?([\w]+)",
        q,
    )
    if m:
        train_id = _resolve_train_id(m.group(1), all_trains)
        state = _resolve_state(m.group(2))
        if train_id and state:
            return {
                "query": query,
                "answer": _format_single_alternative(train_id, state, plan, all_trains, yard_layout),
                "matched_pattern": "why_not_state",
            }

    m = re.search(r"why\s+(?:is|was)\s+(?:train\s+)?([\w\-]+)", q)
    if m:
        train_id = _resolve_train_id(m.group(1), all_trains)
        if train_id:
            return {
                "query": query,
                "answer": _format_full_explanation(train_id, plan, all_trains, yard_layout),
                "matched_pattern": "why_state",
            }

    m = re.search(r"which\s+trains?\s+(?:are|is)\s+in\s+([\w]+)", q)
    if m:
        state = _resolve_state(m.group(1))
        if state:
            matching = [tid for tid, s in plan_by_id.items() if s == state]
            if matching:
                answer = f"The following trains are assigned {state}: {', '.join(sorted(matching))}."
            else:
                answer = f"No trains are currently assigned {state}."
            return {"query": query, "answer": answer, "matched_pattern": "which_trains_in_state", "trains": sorted(matching)}

    m = re.search(r"which\s+trains?\s+have\s+(critical|major|minor)\s+job\s+cards?", q)
    if m:
        severity = m.group(1)
        matching = [t.train_id for t in all_trains if t.job_card_severity == severity]
        if matching:
            answer = f"The following trains have an open {severity}-severity job card: {', '.join(sorted(matching))}."
        else:
            answer = f"No trains currently have an open {severity}-severity job card."
        return {"query": query, "answer": answer, "matched_pattern": "which_trains_severity", "trains": sorted(matching)}

    m = re.search(r"what\s+would\s+happen\s+if\s+([\w\-]+)\s+(?:were|was|is)\s+(?:in\s+)?([\w]+)", q)
    if m:
        train_id = _resolve_train_id(m.group(1), all_trains)
        state = _resolve_state(m.group(2))
        if train_id and state:
            return {
                "query": query,
                "answer": _format_single_alternative(train_id, state, plan, all_trains, yard_layout),
                "matched_pattern": "hypothetical",
            }

    return {
        "query": query,
        "answer": (
            "I couldn't parse that question. Try asking things like "
            "'Why is KMRL-03 in cleaning?', 'Why isn't KMRL-02 in standby?', "
            "'Which trains are in service?', or 'Which trains have critical job cards?'"
        ),
        "matched_pattern": None,
    }
