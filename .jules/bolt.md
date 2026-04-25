## 2026-04-25 - [Database Level Filtering vs In-Memory]
**Learning:** [Fetching unconstrained rows from the database (e.g., using `User.created_at.isnot(None)`) and filtering them in memory causes massive memory bloat and database overhead in large systems like this ORM.]
**Action:** [Always apply specific filters (like dates, statuses, limits) directly in the SQLAlchemy query before calling `.all()` to drastically reduce payload size and execution time.]
