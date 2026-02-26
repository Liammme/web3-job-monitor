from __future__ import annotations
from dataclasses import dataclass

from app.crawlers.base import NormalizedJob


@dataclass
class ScoreResult:
    total_score: float
    keyword_score: float
    seniority_score: float
    remote_bonus: float
    region_bonus: float
    decision: str
    matched_keywords: list[str]


class Scorer:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def score(self, job: NormalizedJob | dict) -> ScoreResult:
        if isinstance(job, dict):
            text = " ".join([
                job.get("title", ""),
                job.get("description", ""),
                job.get("location", ""),
                job.get("remote_type", ""),
            ]).lower()
        else:
            text = " ".join([job.title, job.description, job.location, job.remote_type]).lower()

        strong_score, strong_hits = self._score_keywords(text, self.cfg["strong_keywords"], self.cfg["strong_cap"])
        medium_score, medium_hits = self._score_keywords(text, self.cfg["medium_keywords"], self.cfg["medium_cap"])
        keyword_score = strong_score + medium_score

        seniority_score = 0
        for key, val in self.cfg["seniority"].items():
            if key in text:
                seniority_score = max(seniority_score, val)

        remote_bonus = self.cfg["remote_bonus"] if ("remote" in text or "global" in text) else 0
        region_bonus = self.cfg["global_bonus"] if "global" in text else 0

        total = min(100.0, keyword_score + seniority_score + remote_bonus + region_bonus)
        decision = "high" if total >= self.cfg["threshold"] else "low"

        negative_hit = any(k in text for k in self.cfg["negative_keywords"])
        if negative_hit and keyword_score == 0 and total < self.cfg["reject_if_negative_and_below"]:
            decision = "low"

        return ScoreResult(
            total_score=total,
            keyword_score=keyword_score,
            seniority_score=seniority_score,
            remote_bonus=remote_bonus,
            region_bonus=region_bonus,
            decision=decision,
            matched_keywords=strong_hits + medium_hits,
        )

    @staticmethod
    def _score_keywords(text: str, weights: dict[str, int], cap: int) -> tuple[int, list[str]]:
        score = 0
        hits: list[str] = []
        for key, val in weights.items():
            if key in text:
                score += val
                hits.append(key)
        return min(score, cap), hits
