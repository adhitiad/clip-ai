## 2024-04-21 - Optimize user growth query performance
**Learning:** Loading the entire user list via `.all()` and then filtering in Python memory in endpoints like `dashboard_user_growth` will lead to OOM errors and slow response times as the database grows, as it loads every `User.created_at` timestamp rather than just those in the requested date range.
**Action:** Always apply time-bound filters directly within the SQLAlchemy query (e.g., `User.created_at >= start_date`) before calling `.all()` to reduce database load and memory usage.
