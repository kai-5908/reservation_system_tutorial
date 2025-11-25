# ER diagram (current tables)

```
users
  - id (PK)
  - email (UNIQUE, NOT NULL)
  - name (NOT NULL)
  - phone (NULL)
  - email_verified_at (NULL)
  - password_hash (NOT NULL)
  - auth_provider (NOT NULL, default 'local')
  - auth_provider_id (NULL)
  - created_at
  - updated_at

shops
  - id (PK)
  - name (NOT NULL)
  - created_at
  - updated_at

slots
  - id (PK)
  - shop_id (FK -> shops.id)
  - seat_id (NULL)
  - starts_at (NOT NULL)
  - ends_at (NOT NULL)
  - capacity (NOT NULL)
  - status (ENUM: open/closed/blocked, default open)
  - created_at
  - updated_at
  - Constraints:
      * starts_at < ends_at
      * capacity >= 1
      * UNIQUE(shop_id, seat_id, starts_at, ends_at)
  - Indexes:
      * idx_slots_shop (shop_id)
      * idx_slots_seat (seat_id)

reservations
  - id (PK)
  - slot_id (FK -> slots.id)
  - user_id (FK -> users.id)
  - party_size (NOT NULL)
  - status (ENUM: request_pending/booked/cancelled, default request_pending)
  - version (INT, default 1)
  - created_at
  - updated_at
  - Constraints:
      * party_size >= 1
      * UNIQUE(user_id, slot_id)
  - Indexes:
      * idx_res_slot (slot_id)
      * idx_res_user (user_id)
```

## Relationships (FK)
- slots.shop_id → shops.id (N:1)
- reservations.slot_id → slots.id (N:1)
- reservations.user_id → users.id (N:1)

## Quick ASCII ER
```
users (1) <----- (N) reservations (N) -----> (1) slots (N) -----> (1) shops
                       ^
                       |
                   users.id
```
```
