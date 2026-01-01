from typing import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from .routers import reservations, slots
from .utils.request_id import generate_request_id, set_request_id

app = FastAPI(title="Reservation API")

# CORS for local frontend (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
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
