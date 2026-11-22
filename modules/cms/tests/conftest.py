import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.cms.domain.rules import VERIFY_COMPLAINANT, VERIFY_SUPERVISOR
from modules.cms.registry import ROLE_GRANTS
from modules.cms.services.policy import create_category, publish_policy


@pytest.fixture
def cms_policy(db):
    return publish_policy(
        actor_user_id=999,
        low_sla_hours=72,
        medium_sla_hours=48,
        high_sla_hours=24,
        reminder_lead_hours=4,
        max_attachments=3,
        routine_verification_by=VERIFY_COMPLAINANT,
        escalated_verification_by=VERIFY_SUPERVISOR,
        notify_on_announcement=True,
    )


@pytest.fixture
def cms_category(db):
    return create_category(
        code="NET", name="Network & Wi-Fi", description="Campus network issues"
    )


@pytest.fixture
def cms_category_alt(db):
    return create_category(code="ELEC", name="Electrical", description="Electrical issues")


def auth_client(
    stub_iam,
    *,
    user_id: int,
    role: str,
    kind: str = "student",
    permissions=None,
    modules=("cms",),
    roles=None,
):
    perms = tuple(ROLE_GRANTS[role]) if permissions is None else tuple(permissions)
    stub_iam(
        make_session(
            user_id=user_id,
            kind=kind,
            active_role=role,
            roles=tuple(roles) if roles is not None else (role,),
            permissions=perms,
            modules=tuple(modules),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token tok-{user_id}")
    return client
