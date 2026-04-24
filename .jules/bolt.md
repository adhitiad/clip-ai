# Bolt's Journal

## 2024-04-24 - [Avoid In-Memory Filtering on Time Series Data]
**Learning:** Filtering entire database tables in memory (like retrieving all user records via `.all()` just to bucket the last N days) causes significant overhead and risks Out-Of-Memory (OOM) errors as the data scales.
**Action:** Always apply limits or time-bound filters (e.g. `>= start_date`) directly within the SQLAlchemy query before invoking `.all()` to minimize the dataset fetched from PostgreSQL.
