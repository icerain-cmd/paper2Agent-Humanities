from __future__ import annotations
from pathlib import Path
from ..paper_agent import PaperAgent
from ..schema import ReviewStatus, StatementType

class AgentRegistry:
    def __init__(self, fixture_dir: str | Path):
        self.fixture_dir=Path(fixture_dir)
        self._agents: dict[str,PaperAgent]={}
        self._paths: dict[str,Path]={}
        self._rejected: list[dict[str,str]]=[]
        self.reload()

    def reload(self):
        agents={}
        paths={}
        rejected=[]
        for path in sorted(self.fixture_dir.glob("*-agent.json")):
            if path.name.endswith("-phase2-agent.json"):
                continue
            try:
                agent=PaperAgent.from_json(path)
                if agent.paper_id in agents:
                    raise ValueError(f"duplicate paper_id in registry: {agent.paper_id}")
                agents[agent.paper_id]=agent
                paths[agent.paper_id]=path
            except Exception as exc:
                rejected.append({
                    "file":path.name,
                    "error":f"{type(exc).__name__}: {exc}",
                })
        self._agents=agents
        self._paths=paths
        self._rejected=rejected
        return self

    def ids(self): return tuple(sorted(self._agents))

    def get(self, agent_id: str) -> PaperAgent:
        if agent_id not in self._agents:
            raise KeyError(f"unknown agent_id: {agent_id}")
        return self._agents[agent_id]

    def diagnostics(self):
        return {
            "loaded":len(self._agents),
            "rejected":list(self._rejected),
        }

    def describe(self):
        rows=[]
        for agent_id in sorted(self._agents):
            a=self._agents[agent_id]
            statements=list(a.store.values())
            grounded=[
                s for s in statements
                if s.statement_type in {StatementType.SOURCE_QUOTE,StatementType.AUTHOR_CLAIM}
            ]
            reviewed=[
                s for s in grounded
                if s.review_status==ReviewStatus.REVIEWED
            ]
            rows.append({
                "agent_id":a.paper_id,
                "display_name":f"{a.author} — {a.title}",
                "author":a.author,
                "title":a.title,
                "edition_id":a.edition_id,
                "concepts":list(a.concepts),
                "source_id":a.source_id,
                "statement_count":len(statements),
                "grounded_statement_count":len(grounded),
                "reviewed_grounded_count":len(reviewed),
                "source_file":self._paths[a.paper_id].name,
            })
        return rows
