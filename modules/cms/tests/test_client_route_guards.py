import re
from pathlib import Path

from modules.cms.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = (
    Path(__file__).resolve().parents[3] / "client" / "src" / "modules" / "cms" / "routes.tsx"
)
GUARDED_PAGES = {
    "complaints",
    "escalations",
    "reopen-requests",
    "feedback",
    "announcements",
    "reports",
    "policy",
}


def guarded_routes() -> dict[str, str]:
    pattern = r'\{\s*path:\s*"([^"]+)",\s*element:\s*guarded\(\s*"([^"]+)"'
    return dict(re.findall(pattern, ROUTES.read_text()))


def nav_permission(path: str) -> str | None:
    base = MODULE.get("base_path", "/cms").rstrip("/")
    for item in NAV_ITEMS:
        if item.get("to") == f"{base}/{path}":
            return item.get("required_permission")
    return None


def test_every_cms_page_is_guarded():
    assert set(guarded_routes()) >= GUARDED_PAGES


def test_each_cms_guard_matches_its_nav_item_permission():
    declared = {code for code, _ in PERMISSIONS}
    for path, permission in guarded_routes().items():
        assert permission in declared, f"{path}: {permission} is not declared"
        assert permission == nav_permission(path), f"{path}: guard and nav item disagree"
