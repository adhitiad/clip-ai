# Model Data Internal — @dataclass + numpy + pandas

Pytest/route memakai Pydantic untuk kontrak HTTP. **Model internal** memakai
`@dataclass` di `backend/core/models.py`. Olahan numerik memakai **numpy**,
agregasi tabular memakai **pandas**.

## Model @dataclass

| Model | Dipakai di | Fungsi |
| --- | --- | --- |
| `ViralFeatures` | `services/viral_predictor.py` | 10 fitur positional; `as_array()` → numpy |
| `ViralScore` | predictor | hasil skor + threshold + confidence |
| `ShortsClipPlan`, `ShortsPlan` | `core/agent.py`, `routes/agent.py` | rencana short-form; `as_dict()` untuk response API; `thumbnail_path`/`thumbnail_url` (thumbnail per klip dari `video_engine.py`) |
| `ProviderInfo` | katalog provider | metadata LLM/TTS/STT |
| `ClipStat` | `routes/dashboard.py` | ringkasan clip + `day_key()` |
| `Clip` (ORM) | `models/clip.py` | tabel `clips`; `created_at` (migrasi `0009`) dipakai statistik 7 hari |
| `RevenueSnapshot` | `services/platform_revenue.py` | pendapatan platform read-only; `available=False` berarti dilewati |
| `PerformanceFeedbackRecord` | `models/feedback.py` | feedback nyata untuk kalibrasi (bukan training) |

## Index query (migrasi `0010`)

| Index | Tabel | Dipakai untuk |
| --- | --- | --- |
| `ix_task_results_status_updated_at` | `task_results` | filter status + urutan terbaru pada `GET /ops/tasks` |
| `ix_performance_feedback_created_at` | `performance_feedback` | agregasi kalibrasi per periode |
| `ix_clips_created_at` | `clips` | statistik 7 hari `GET /dashboard/stats` |

## Alur Pydantic → dataclass

LLM menghasilkan `backend.core.agent.ShortsPlan` (Pydantic, untuk
`with_structured_output`). `to_dataclass()` mengubahnya jadi
`backend.core.models.ShortsPlan` (frozen + slots). Route `/agent/shorts`
memanggil `plan.as_dict()` untuk response JSON.

## numpy

- `ViralFeatures.as_array()` → vektor 10 elemen.
- `rule_based_score()` → `np.dot(vector, resolve_score_weights())` + `np.clip(1, 10)`.
- `resolve_score_weights()` → override `VIRAL_SCORE_WEIGHTS` (10 angka 0–3), invalid → default.
- `calibration_report()` → pandas `corr()` + bucket `pd.cut()` atas `performance_feedback`.
- `clip_duration_stats()` → `np.mean/min/max` durasi klip.
- Dashboard `/stats` → `np.sum/np.max` untuk total & peak harian.

## pandas

- `batch_predict_and_filter()` → `pd.DataFrame(scored).sort_values(...)`.
- `_get_clip_summary()` → `pd.Series` skor untuk mean/max.
- `/dashboard/stats` → `pd.Series.value_counts().sort_index()` untuk agregasi per hari.

## Aturan

- Jangan memakai Pydantic untuk model internal baru; pakai `@dataclass`.
- Tetap pakai Pydantic untuk request/response FastAPI.
- Konversi dataclass → JSON lewat `asdict()` + helper `as_dict()`.
- Urutan fitur viral tetap 10 positional; `ViralFeatures.from_list()` menjaganya.

## Test

`tests/test_dataclass_models.py` menguji konversi dataclass, vektor numpy,
urutan pandas, dan helper tanggal.
