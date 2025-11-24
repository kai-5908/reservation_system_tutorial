from fastapi import FastAPI

from .routers import reservations, slots

app = FastAPI(title="Reservation API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(slots.router)
app.include_router(reservations.router)
