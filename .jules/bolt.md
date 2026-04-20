## 2024-05-15 - Cached Redundant Subprocess Calls in ML Feature Extraction
**Learning:** During batch prediction (`batch_predict_and_filter`), the ML pipeline iterates over multiple candidate clips generated from the same source audio file. Naively extracting features for each clip runs a costly `ffmpeg` subprocess for the *same* `audio_path` multiple times.
**Action:** Always memoize/cache expensive I/O or subprocess calls (e.g. using `functools.lru_cache`) when extracting features from a source file that is reused across multiple iterations in a pipeline.
