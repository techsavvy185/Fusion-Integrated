from __future__ import annotations

from dataclasses import dataclass, field

# BR-CMS-012, AFR-CMS-022: canonical complaint lifecycle states.
SUBMITTED = "submitted"
IN_PROGRESS = "in_progress"
RESOLVED = "resolved"
REJECTED = "rejected"
CLOSED = "closed"

STATUSES = (SUBMITTED, IN_PROGRESS, RESOLVED, REJECTED, CLOSED)
UNRESOLVED_STATUSES = frozenset({SUBMITTED, IN_PROGRESS})
TERMINAL_STATUSES = frozenset({REJECTED})

# BR-CMS-009, AFR-CMS-013: closed priority value set.
LOW = "Low"
MEDIUM = "Medium"
HIGH = "High"
PRIORITIES = (LOW, MEDIUM, HIGH)
VALID_PRIORITIES = frozenset(PRIORITIES)

# BR-CMS-025, CW-CMS-03: orthogonal escalation types.
ESCALATION_MANUAL = "manual"
ESCALATION_AUTOMATIC = "automatic"
ESCALATION_TYPES = (ESCALATION_MANUAL, ESCALATION_AUTOMATIC)

# Actors for transition enforcement.
COMPLAINANT = "complainant"
HANDLER = "handler"
SUPERVISOR = "supervisor"
SYSTEM = "system"


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot move a complaint from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, to: str):
        super().__init__(f"A {actor_kind} may not move a complaint from {frm!r} to {to!r}.")
        self.actor_kind, self.frm, self.to = actor_kind, frm, to


class GuardFailed(Exception):
    def __init__(self, guard: str, message: str = ""):
        super().__init__(message or f"Guard {guard!r} failed.")
        self.guard = guard


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)


# CW-CMS-01, CW-CMS-02, BW-CMS-01..06: declarative state transition table.
TRANSITIONS: tuple[Transition, ...] = (
    # UC-CMS-005, BR-CMS-011, ISS-CMS-007: progress update enters and stays in_progress.
    Transition(
        SUBMITTED,
        IN_PROGRESS,
        "cms.complaint.update",
        frozenset({HANDLER}),
        ("has_handling_setup",),
    ),
    Transition(
        IN_PROGRESS,
        IN_PROGRESS,
        "cms.complaint.update",
        frozenset({HANDLER}),
        ("has_progress_note",),
    ),
    # UC-CMS-006, BR-CMS-013, BW-CMS-01: resolve requires non-empty details.
    Transition(
        SUBMITTED,
        RESOLVED,
        "cms.complaint.update",
        frozenset({HANDLER}),
        ("has_handling_setup", "has_resolution_details"),
    ),
    Transition(
        IN_PROGRESS,
        RESOLVED,
        "cms.complaint.update",
        frozenset({HANDLER}),
        ("has_resolution_details",),
    ),
    # UC-CMS-006, BR-CMS-014, BW-CMS-04: reject requires non-empty reason.
    Transition(
        SUBMITTED,
        REJECTED,
        "cms.complaint.update",
        frozenset({HANDLER}),
        ("has_rejection_reason",),
    ),
    Transition(
        IN_PROGRESS,
        REJECTED,
        "cms.complaint.update",
        frozenset({HANDLER}),
        ("has_rejection_reason",),
    ),
    # UC-CMS-007, UC-CMS-019, BR-CMS-016, BW-CMS-02, BW-CMS-03: closure verification.
    Transition(
        RESOLVED,
        CLOSED,
        "cms.complaint.approve",
        frozenset({COMPLAINANT, SUPERVISOR}),
        ("matches_required_verifier",),
    ),
    # UC-CMS-020, BR-CMS-019, BR-CMS-020, BW-CMS-05, ISS-CMS-008: supervisor approves reopening.
    Transition(
        CLOSED,
        IN_PROGRESS,
        "cms.reopen_request.approve",
        frozenset({SUPERVISOR}),
        ("has_pending_reopen_request",),
    ),
)

_BY_EDGE: dict[tuple[str, str], Transition] = {(t.frm, t.to): t for t in TRANSITIONS}


def find_transition(frm: str, to: str) -> Transition:
    edge = _BY_EDGE.get((frm, to))
    if edge is None:
        raise InvalidTransition(frm, to)
    return edge


def check_transition(
    frm: str, to: str, actor_kind: str, passed_guards: dict[str, bool] | None = None
) -> Transition:
    edge = find_transition(frm, to)
    if actor_kind not in edge.actors:
        raise ActorNotAllowed(actor_kind, frm, to)
    guards = passed_guards or {}
    for guard in edge.guards:
        if not guards.get(guard, False):
            raise GuardFailed(guard)
    return edge
