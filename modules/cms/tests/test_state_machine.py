import pytest

from modules.cms.domain.state_machine import (
    STATUSES,
    TRANSITIONS,
    ActorNotAllowed,
    GuardFailed,
    InvalidTransition,
    check_transition,
    find_transition,
)
from modules.cms.registry import PERMISSIONS


def test_every_illegal_transition_is_refused():
    # Step 5.4, BR-CMS-012, CW-CMS-01, CW-CMS-02: enumerate all pairs not in TRANSITIONS.
    legal_pairs = {(t.frm, t.to) for t in TRANSITIONS}
    for frm in STATUSES:
        for to in STATUSES:
            if (frm, to) not in legal_pairs:
                with pytest.raises(InvalidTransition):
                    find_transition(frm, to)


def test_every_legal_transition_enforces_actor_and_guards():
    # Step 5.4, BW-CMS-01..06: verify every edge's actor restriction, guards, and valid permission.
    declared_permissions = {code for code, _ in PERMISSIONS}
    for t in TRANSITIONS:
        assert t.permission in declared_permissions
        actor = next(iter(t.actors))
        all_passed = dict.fromkeys(t.guards, True)
        assert check_transition(t.frm, t.to, actor, all_passed) == t

        with pytest.raises(ActorNotAllowed):
            check_transition(t.frm, t.to, "unauthorized_actor", all_passed)

        for missing_guard in t.guards:
            partial = {g: (g != missing_guard) for g in t.guards}
            with pytest.raises(GuardFailed) as exc:
                check_transition(t.frm, t.to, actor, partial)
            assert exc.value.guard == missing_guard
