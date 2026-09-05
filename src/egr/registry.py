from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .models import AgentSpec, RoutingRequest


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "can",
    "do",
    "for",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "please",
    "that",
    "the",
    "this",
    "to",
    "was",
    "what",
    "where",
    "why",
    "with",
    "your",
}


def normalize(value: str) -> str:
    return " ".join(TOKEN_PATTERN.findall(value.lower()))


def tokens(value: str) -> set[str]:
    return {token for token in TOKEN_PATTERN.findall(value.lower()) if token not in STOPWORDS}


def phrase_similarity(text: str, phrase: str) -> float:
    normalized_text = normalize(text)
    normalized_phrase = normalize(phrase)
    if not normalized_phrase:
        return 0.0
    if normalized_phrase in normalized_text:
        return 1.0
    phrase_tokens = tokens(normalized_phrase)
    if not phrase_tokens:
        return 0.0
    return len(tokens(normalized_text) & phrase_tokens) / len(phrase_tokens)


@dataclass(frozen=True, slots=True)
class AgentRegistry:
    version: str
    agents: tuple[AgentSpec, ...]
    cost_model_version: str = "cost-model@unspecified"
    cost_unit: str = "unspecified"

    @classmethod
    def from_path(cls, path: str | Path) -> "AgentRegistry":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            version=payload["version"],
            agents=tuple(AgentSpec.from_dict(item) for item in payload["agents"]),
            cost_model_version=payload.get("cost_model_version", "cost-model@unspecified"),
            cost_unit=payload.get("cost_unit", "unspecified"),
        )

    def get(self, agent_id: str) -> AgentSpec | None:
        return next((agent for agent in self.agents if agent.agent_id == agent_id), None)

    def detect_explicit_agent(self, request: RoutingRequest) -> str | None:
        if request.explicit_agent_id:
            return request.explicit_agent_id
        normalized_text = normalize(request.text)
        control_verbs = ("use", "using", "ask", "route to", "send to", "delegate to")
        for agent in self.agents:
            for name in (agent.agent_id, *agent.aliases):
                normalized_name = normalize(name)
                if any(
                    phrase in normalized_text
                    for verb in control_verbs
                    for phrase in (f"{verb} {normalized_name}", f"{verb} the {normalized_name}")
                ):
                    return agent.agent_id
        return None


@dataclass(frozen=True, slots=True)
class RetrievedCandidate:
    agent: AgentSpec
    rank: int
    score: float


class CandidateRetriever:
    version = "hybrid-token-capability@0.1.0"

    def __init__(self, top_k: int = 5):
        if top_k < 1:
            raise ValueError("top_k must be positive")
        self.top_k = top_k

    def _score(self, text: str, agent: AgentSpec) -> float:
        phrases = [agent.description, *agent.aliases, *agent.domains]
        for capability in agent.capabilities:
            phrases.extend((capability.description, *capability.keywords))
        matches = sorted((phrase_similarity(text, phrase) for phrase in phrases), reverse=True)
        strongest = matches[0] if matches else 0.0
        supporting = sum(score for score in matches[1:4] if score >= 0.5)
        return min(1.0, strongest * 0.8 + supporting * 0.1)

    def retrieve(
        self,
        request: RoutingRequest,
        registry: AgentRegistry,
        explicit_agent_id: str | None,
    ) -> tuple[RetrievedCandidate, ...]:
        scored = sorted(
            ((agent, self._score(request.text, agent)) for agent in registry.agents),
            key=lambda item: (-item[1], item[0].agent_id),
        )
        selected = list(scored[: self.top_k])
        if explicit_agent_id and all(agent.agent_id != explicit_agent_id for agent, _ in selected):
            explicit = next((item for item in scored if item[0].agent_id == explicit_agent_id), None)
            if explicit:
                selected[-1] = explicit
                selected.sort(key=lambda item: (-item[1], item[0].agent_id))
        return tuple(
            RetrievedCandidate(agent=agent, rank=index, score=round(score, 6))
            for index, (agent, score) in enumerate(selected, start=1)
        )
