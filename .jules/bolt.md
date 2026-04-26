## 2024-10-27 - [Time-bounds for Analytic Queries]
**Learning:** Fetching an entire table and doing memory-based time-bound filtering on it is an anti-pattern. Even if the table is small now, it leads to OOM crashes in production later when scaling up analytical endpoints.
**Action:** Always apply time-bounds (like `created_at >= X`) directly within the SQLAlchemy query before calling `.all()` to avoid fetching unnecessary rows from the database.
