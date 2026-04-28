## 2026-04-28 - [SQLAlchemy In-Memory Filtering Anti-Pattern]
**Learning:** Found an anti-pattern where unbounded queries (`db.query(...).all()`) fetch entire tables into memory just to aggregate a subset of the data in Python (e.g., date bucketing for dashboards).
**Action:** Always filter large datasets at the database level using `filter(...)` and convert Python `datetime.date` to `datetime.datetime` bounds when querying timestamp columns, avoiding massive memory bloat as the system scales.
