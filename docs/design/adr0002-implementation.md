# Implementation Design: ADR 0002 (Consistency and Time)

## Scope
- Backend alignment to ADR0002: optimistic cancel with If-Match preferred version check, UTC storage with JST I/O, tz-aware input enforcement.
- Target code: `app/usecases/reservations.py`, `app/routers/reservations.py`, `app/utils/time.py`, `app/infrastructure/repositories.py`.
- Schema already covered by ADR0001 / migration-0001.sql; no new migration required.

## Current state and gaps
- UTC storage + JST response mostly present (`utc_naive_to_jst` + Pydantic encoders).
- Booking uses slot row lock + remaining seats + duplicate check.
- Missing/changed: cancel must check `version`, enforce cutoff (2 days before start), and reject tz-less datetimes with 400.

## Booking flow (recap)
1. Begin transaction.
2. Lock slot with `SELECT ... FOR UPDATE WHERE id=:slot_id`.
3. In the same transaction, read aggregates:
   - `user_has_active`: any reservation where `status != cancelled`.
   - `sum_reserved`: sum `party_size` where `status != cancelled`.
4. Build `SlotSnapshot`, run `validate_reservation` (status=open, no duplicate, capacity, party_size>0).
5. Insert reservation with `status=booked`, `version=1`, UTC-naive timestamps.

## Cancel flow (optimistic)
1. Begin transaction, load reservation+slot with `FOR UPDATE`.
2. Ownership check (user_id).
3. Version: If-Match preferred, else body.version; missing -> 400, mismatch -> 409.
4. Idempotent: if already `cancelled`, return as-is.
5. Cutoff: user cancel is allowed only before 2 days prior to `starts_at`; otherwise raise CancelNotAllowed (403). Shop cancel can always set `cancelled`.
6. Set status `cancelled`, `version += 1`, `updated_at = now_utc_naive()`, persist.

## Time handling
- Store UTC naive (`DateTime(timezone=False)`).
- Input must be tz-aware; naive -> 400.
- Convert with `to_utc_naive` for DB writes/queries; `utc_naive_to_jst` for responses.
- Keep Pydantic encoders to emit ISO 8601 +09:00.

## API contract adjustments
- `POST /me/reservations/{reservation_id}/cancel`:
  - version required (If-Match preferred, else body.version).
  - 409 on version conflict; 400 on missing/invalid tz or version; 403 on cutoff; 404 on not found/not owned.
- (Optional) add `created_at`/`updated_at` (JST) to responses if audit is needed.

## Testing
- Domain/service: version conflict, idempotent cancel, naive datetime rejection.
- Usecase: capacity overflow, duplicate booking, cancel with matching/mismatching version, cutoff behavior.
- (Optional) DB/integration: concurrent booking lock behavior preserves capacity.

## Infrastructure notes
- Assume MySQL InnoDB REPEATABLE READ; slot row locks serialize booking.
- Existing indexes (`idx_slots_shop`, `idx_slots_seat`, `idx_res_slot`, `idx_res_user`) are sufficient.
