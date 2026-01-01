from fastapi import FastAPI, Request

from .utils.request_id import generate_request_id, set_request_id
from .routers import reservations, slots

app = FastAPI(title="Reservation API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    incoming = request.headers.get("X-Request-ID")
    request_id = incoming.strip() if incoming else generate_request_id()
    set_request_id(request_id)
    try:
        response = await call_next(request)
    finally:
        # Ensure contextvar is cleared for next request
        set_request_id(None)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(slots.router)
app.include_router(reservations.router)
