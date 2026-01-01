from app.deps import get_current_user_id
from app.routers import slots
from fastapi.routing import APIRoute


def test_slots_router_requires_bearer_token() -> None:
    # Router-level dependency must include Bearer token verification
    assert any(dep.dependency == get_current_user_id for dep in slots.router.dependencies)

    # Each route should inherit the auth dependency
    for route in slots.router.routes:
        if not isinstance(route, APIRoute):
            continue
        assert any(dep.call == get_current_user_id for dep in route.dependant.dependencies)
