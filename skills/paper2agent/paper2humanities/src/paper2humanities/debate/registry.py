from __future__ import annotations
from pathlib import Path
from ..paper_agent import PaperAgent

class AgentRegistry:
    def __init__(self, fixture_dir: str | Path):
        self.fixture_dir=Path(fixture_dir)
        self._agents: dict[str,PaperAgent]={}
        self.reload()

    def reload(self):
        self._agents={}
        for path in sorted(self.fixture_dir.glob("*-agent.json")):
            if path.name.endswith("-phase2-agent.json"):
                continue
            try:
                agent=PaperAgent.from_json(path)
            except Exception:
                continue
            if agent.paper_id in self._agents:
                raise ValueError(f"duplicate paper_id in registry: {agent.paper_id}")
            self._agents[agent.paper_id]=agent
        return self

    def ids(self): return tuple(sorted(self._agents))
    def get(self, agent_id: str) -> PaperAgent:
        if agent_id not in self._agents: raise KeyError(f"unknown agent_id: {agent_id}")
        return self._agents[agent_id]
    def describe(self):
        return [{"agent_id":a.paper_id,"display_name":f"{a.author} — {a.title}","author":a.author,
                 "title":a.title,"edition_id":a.edition_id,"concepts":list(a.concepts),
                 "source_id":a.source_id} for a in self._agents.values()]
