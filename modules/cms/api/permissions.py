from rest_framework.permissions import BasePermission


class _AnyPermission(BasePermission):
    codes: tuple[str, ...] = ()
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        principal = getattr(request, "principal", None)
        if principal is None:
            return False
        return principal.has_any_permission(*self.codes)


def HasAnyPermission(*codes: str):  # noqa: N802
    name = "HasAnyPermission_" + "_".join(c.replace(".", "_") for c in codes)
    return type(name, (_AnyPermission,), {"codes": codes})
