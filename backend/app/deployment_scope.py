from __future__ import annotations

DEPLOYMENT_SCOPE_VERSION = "deployment-scope-v0.1"


def deployment_contract() -> dict[str, object]:
    """Declare deployment truth; this is not a switch that enables tenancy."""
    return {
        "version": DEPLOYMENT_SCOPE_VERSION,
        "scope": "SINGLE_USER_DOGFOOD",
        "authenticated_user_identity": False,
        "multi_user_isolation": False,
        "state_ownership_boundary": "DEFINED_NOT_TENANTIZED",
    }
