## 2024-05-23 - Prevented in-memory data fetching in user dashboard
**Learning:** Found an anti-pattern in `routes/dashboard.py` where `.all()` was fetching the entire user base into memory before filtering out by creation date, which causes high memory consumption.
**Action:** Always verify if filters like timeframes can be applied directly to the query inside the database before `.all()` is called, and delete any leftover testing scratchpads before submitting PRs.
