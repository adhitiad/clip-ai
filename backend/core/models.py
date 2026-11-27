"""Model data internal memakai @dataclass (bukan Pydantic/SQLAlchemy).

Dipakai oleh viral predictor, agent shorts, dan dashboard/analitik.
Pydantic tetap dipakai untuk kontrak HTTP di routes/.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import numpy as np


@dataclass(frozen=True, slots=True)
class ViralFeatures:
    """10 fitur positional untuk rule-based scoring."""

    duration_score: float
    title_power_words: int
    desc_power_words: int
    title_length_score: float
    has_broll: float
    audio_energy: float
    audio_pitch: float
    face_emotion: float
    face_count_norm: float
    hook_ratio: float

    def as_array(self) -> np.ndarray:
        return np.array(
            [
                self.duration_score,
                self.title_power_words,
                self.desc_power_words,
                self.title_length_score,
                self.has_broll,
                self.audio_energy,
                self.audio_pitch,
                self.face_emotion,
                self.face_count_norm,
                self.hook_ratio,
            ],
            dtype=float,
        )

    @classmethod
    def from_list(cls, values: list[float]) -> "ViralFeatures":
        if len(values) != 10:
            raise ValueError("ViralFeatures butuh tepat 10 nilai")
        return cls(*(float(value) for value in values))


@dataclass(slots=True)
class ViralScore:
    score: float
    threshold: float
    should_render: bool
    confidence: str = "rule_based"
    features: ViralFeatures | None = None

    def as_dict(self) -> dict:
        data = asdict(self)
        if self.features:
            data["features"] = self.features.as_array().tolist()
        return data


@dataclass(frozen=True, slots=True)
class ShortsClipPlan:
    start_time: int
    end_time: int
    hook: str
    title: str
    caption: str
    hashtags: tuple[str, ...] = ()
    thumbnail_path: str | None = None
    thumbnail_url: str | None = None

    def as_dict(self) -> dict:
        return asdict(self) | {"hashtags": list(self.hashtags)}


@dataclass(frozen=True, slots=True)
class ShortsPlan:
    platform: str
    topic: str
    clips: tuple[ShortsClipPlan, ...]
    style_notes: str = ""

    def as_dict(self) -> dict:
        return asdict(self) | {"clips": [clip.as_dict() for clip in self.clips]}


@dataclass(slots=True)
class ProviderInfo:
    """Info provider LLM/TTS/STT."""

    id: str
    name: str
    icon: str
    kind: str
    free: bool = False
    models: tuple[str, ...] = field(default_factory=tuple)
    latency_hint: str = ""
    cost_tier: str = "unknown"
    healthy: bool = True


@dataclass(slots=True)
class ClipStat:
    """Ringkasan satu clip untuk dashboard."""

    clip_id: int
    title: str
    score: int
    created_at: datetime | None = None

    def day_key(self) -> str:
        value = self.created_at or datetime.now(timezone.utc)
        return value.date().isoformat()


@dataclass(frozen=True, slots=True)
class RevenueSnapshot:
    """Pendapatan platform (read-only). ``available=False`` = sengaja dilewati."""

    platform: str
    available: bool
    status: str
    amount: float | None
    currency: str | None
    period_start: str
    period_end: str
    source: str
    note: str = ""

    def as_dict(self) -> dict:
        return asdict(self)
