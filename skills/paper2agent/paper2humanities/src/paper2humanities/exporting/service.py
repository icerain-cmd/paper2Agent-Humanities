from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from pathlib import Path
import json, re

from ..debate.models import DebateSession

def _now():
    return datetime.now(timezone.utc).isoformat()

def _slug(text:str,limit:int=80)->str:
    s=re.sub(r"[^0-9A-Za-z가-힣._-]+","-",text.strip()).strip("-")
    return (s or "debate")[:limit]

class DebateExporter:
    def __init__(self, registry, session_store):
        self.registry=registry
        self.sessions=session_store

    def _participant(self,agent_id:str)->dict:
        try:
            a=self.registry.get(agent_id)
            return {
                "agent_id":a.paper_id,
                "author":a.author,
                "title":a.title,
                "edition_id":a.edition_id,
                "source_id":a.source_id,
            }
        except Exception:
            return {"agent_id":agent_id,"author":None,"title":None,"edition_id":None,"source_id":None}

    def _participant_map(self,session:DebateSession)->dict[str,dict]:
        return {aid:self._participant(aid) for aid in session.participant_ids}

    def _display_name(self,participant:dict)->str:
        if participant.get("author") and participant.get("title"):
            return f"{participant['author']} — {participant['title']}"
        return participant["agent_id"]

    def _evidence_index(self,session:DebateSession)->list[dict]:
        seen=set()
        rows=[]
        for turn in session.turns:
            for ev in turn.evidence:
                key=(ev.get("statement_id"),ev.get("paper_id"),ev.get("page"),ev.get("evidence_span"))
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "statement_id":ev.get("statement_id"),
                    "paper_id":ev.get("paper_id"),
                    "source_id":ev.get("source_id"),
                    "edition_id":ev.get("edition_id"),
                    "page":ev.get("page"),
                    "statement_type":ev.get("statement_type"),
                    "evidence_voice":ev.get("evidence_voice"),
                    "text":ev.get("text"),
                    "evidence_span":ev.get("evidence_span"),
                    "citation":ev.get("citation"),
                })
        return rows

    def build_json(self,session:DebateSession)->dict:
        participants=self._participant_map(session)
        return {
            "export_schema":"paper2agent-humanities-debate-export-v1",
            "exported_at":_now(),
            "session":session.to_dict(),
            "participants":[participants[x] for x in session.participant_ids],
            "evidence_index":self._evidence_index(session),
            "events":self.sessions.events_after(session.session_id,0),
        }

    def _interventions_after(self,session:DebateSession,turn_count:int)->list[dict]:
        return [x for x in session.interventions if int(x.get("at_turn",0))==turn_count]

    def build_markdown(self,session:DebateSession)->str:
        participants=self._participant_map(session)
        lines=[
            f"# {session.topic}",
            "",
            f"- Session ID: `{session.session_id}`",
            f"- Protocol: V{session.protocol_version}",
            f"- Status: {session.status}",
            f"- Turns: {session.current_turn}/{session.max_turns}",
            "",
            "## Participants",
            "",
        ]
        for aid in session.participant_ids:
            p=participants[aid]
            lines.append(f"- **{self._display_name(p)}** (`{aid}`)")
            if p.get("edition_id"):
                lines.append(f"  - Edition: `{p['edition_id']}`")
            if p.get("source_id"):
                lines.append(f"  - Source: `{p['source_id']}`")
        lines += ["","## Debate Transcript",""]

        for intr in self._interventions_after(session,0):
            lines += [f"> **User intervention:** {intr.get('text','')}",""]

        for idx,turn in enumerate(session.turns,1):
            p=participants.get(turn.speaker_agent_id) or self._participant(turn.speaker_agent_id)
            lines += [
                f"### Turn {idx} — {self._display_name(p)}",
                "",
                f"**Action:** {turn.action.value}  ",
                f"**Verification:** {turn.verification_status}  ",
            ]
            if turn.thesis:
                lines.append(f"**Thesis:** {turn.thesis}  ")
            if turn.target_claim:
                lines.append(f"**Target claim:** {turn.target_claim}  ")
            if turn.stance_update:
                lines.append(f"**Stance update:** {turn.stance_update}  ")
            if turn.unresolved_point:
                lines.append(f"**Open issue:** {turn.unresolved_point}  ")
            lines += ["",turn.text,""]
            if turn.support_ids:
                lines += ["**Grounding**",""]
                for ev in turn.evidence:
                    sid=ev.get("statement_id") or "unknown"
                    page=ev.get("page")
                    page_text=f"p.{page}" if page else "page n/a"
                    lines.append(f"- `{sid}` · {page_text}")
                    if ev.get("evidence_span"):
                        lines.append(f"  - Evidence: {ev['evidence_span']}")
                lines.append("")
            for intr in self._interventions_after(session,idx):
                lines += [f"> **User intervention:** {intr.get('text','')}",""]

        lines += ["## Source / Provenance Appendix",""]
        for ev in self._evidence_index(session):
            sid=ev.get("statement_id") or "unknown"
            page=ev.get("page")
            lines += [f"### `{sid}`",""]
            bits=[]
            if ev.get("paper_id"): bits.append(f"paper `{ev['paper_id']}`")
            if ev.get("source_id"): bits.append(f"source `{ev['source_id']}`")
            if ev.get("edition_id"): bits.append(f"edition `{ev['edition_id']}`")
            if page: bits.append(f"PDF p.{page}")
            if bits: lines.append("- "+" · ".join(bits))
            if ev.get("citation"): lines.append(f"- Citation: {ev['citation']}")
            if ev.get("evidence_span"): lines.append(f"- Evidence span: {ev['evidence_span']}")
            lines.append("")
        return "\n".join(lines).rstrip()+"\n"

    def build_html(self,session:DebateSession)->str:
        participants=self._participant_map(session)
        parts=[]
        for aid in session.participant_ids:
            p=participants[aid]
            sub=[]
            if p.get("edition_id"): sub.append(f"edition {escape(str(p['edition_id']))}")
            if p.get("source_id"): sub.append(f"source {escape(str(p['source_id']))}")
            parts.append(f"<li><strong>{escape(self._display_name(p))}</strong><div class='small'>{' · '.join(sub)}</div></li>")
        timeline=[]
        for intr in self._interventions_after(session,0):
            timeline.append(f"<div class='intervention'><strong>User intervention</strong><div>{escape(str(intr.get('text','')))}</div></div>")
        for idx,turn in enumerate(session.turns,1):
            p=participants.get(turn.speaker_agent_id) or self._participant(turn.speaker_agent_id)
            meta=[]
            if turn.thesis: meta.append(f"<div><b>Thesis</b> {escape(turn.thesis)}</div>")
            if turn.target_claim: meta.append(f"<div><b>Target claim</b> {escape(turn.target_claim)}</div>")
            if turn.stance_update: meta.append(f"<span class='chip'>{escape(turn.stance_update)}</span>")
            if turn.unresolved_point: meta.append(f"<div><b>Open issue</b> {escape(turn.unresolved_point)}</div>")
            grounds=[]
            for ev in turn.evidence:
                sid=escape(str(ev.get("statement_id") or "unknown"))
                page=escape(str(ev.get("page") or "—"))
                span=escape(str(ev.get("evidence_span") or ""))
                grounds.append(f"<li><code>{sid}</code> · p.{page}<div class='span'>{span}</div></li>")
            grounding=("<details open><summary>Grounding</summary><ul>"+''.join(grounds)+"</ul></details>") if grounds else ""
            timeline.append(
                "<section class='turn'>"
                f"<div class='turnhead'><div><strong>Turn {idx} · {escape(self._display_name(p))}</strong></div><div class='action'>{escape(turn.action.value)}</div></div>"
                f"<div class='verify'>{escape(turn.verification_status)}</div>"
                f"<div class='meta'>{''.join(meta)}</div>"
                f"<div class='body'>{escape(turn.text).replace(chr(10),'<br>')}</div>"
                f"{grounding}</section>"
            )
            for intr in self._interventions_after(session,idx):
                timeline.append(f"<div class='intervention'><strong>User intervention</strong><div>{escape(str(intr.get('text','')))}</div></div>")

        appendix=[]
        for ev in self._evidence_index(session):
            sid=escape(str(ev.get("statement_id") or "unknown"))
            page=escape(str(ev.get("page") or "—"))
            span=escape(str(ev.get("evidence_span") or ""))
            citation=escape(str(ev.get("citation") or ""))
            appendix.append(f"<div class='source'><strong><code>{sid}</code></strong> · p.{page}<div class='small'>{citation}</div><div class='span'>{span}</div></div>")

        return f"""<!doctype html>
<html lang='ko'><head><meta charset='utf-8'><style>
@page {{ size:A4; margin:16mm 15mm 18mm; }}
* {{ box-sizing:border-box; }}
body {{ font-family:"Noto Sans CJK KR","Noto Sans KR","Malgun Gothic","Apple SD Gothic Neo",sans-serif; color:#20201d; font-size:10.5pt; line-height:1.58; }}
h1 {{ font-size:20pt; line-height:1.25; margin:0 0 8px; }}
h2 {{ font-size:14pt; margin:24px 0 10px; border-bottom:1px solid #ddd; padding-bottom:4px; }}
ul {{ padding-left:20px; }}
.small {{ color:#686862; font-size:8.5pt; }}
.summary {{ background:#f5f5f1; border:1px solid #ddd; border-radius:8px; padding:10px 12px; margin:10px 0 18px; }}
.turn {{ break-inside:avoid; border:1px solid #d8d8d2; border-radius:9px; padding:12px 14px; margin:0 0 12px; }}
.turnhead {{ display:flex; justify-content:space-between; gap:10px; }}
.action,.chip {{ display:inline-block; background:#eeeeea; border-radius:999px; padding:2px 7px; font-size:8pt; font-weight:700; }}
.verify {{ color:#14733a; font-size:8pt; font-weight:700; margin-top:4px; }}
.meta {{ background:#f8f8f5; border-left:3px solid #c9c9c2; padding:7px 9px; margin:8px 0; font-size:9pt; }}
.body {{ margin-top:8px; }}
.span {{ background:#f6f6f2; border-radius:5px; padding:5px 7px; margin-top:3px; font-size:8.5pt; }}
.intervention {{ border-left:3px solid #888; padding:6px 9px; margin:10px 0; background:#fafafa; }}
.source {{ break-inside:avoid; margin:0 0 10px; }}
code {{ font-family:ui-monospace,Consolas,monospace; font-size:8.5pt; }}
details summary {{ font-size:8.5pt; margin-top:7px; }}
</style></head><body>
<h1>{escape(session.topic)}</h1>
<div class='summary'>
<div><strong>Session</strong> {escape(session.session_id)}</div>
<div><strong>Protocol</strong> V{escape(session.protocol_version)} · <strong>Status</strong> {escape(session.status)} · <strong>Turns</strong> {session.current_turn}/{session.max_turns}</div>
</div>
<h2>Participants</h2><ul>{''.join(parts)}</ul>
<h2>Debate Transcript</h2>
{''.join(timeline)}
<h2>Source / Provenance Appendix</h2>
{''.join(appendix)}
</body></html>"""

    def write_pdf(self,session:DebateSession,target:Path)->Path:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError("Playwright is required for PDF export") from exc
        target.parent.mkdir(parents=True,exist_ok=True)
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page()
            page.set_content(self.build_html(session),wait_until="load")
            page.emulate_media(media="print")
            page.pdf(path=str(target),format="A4",print_background=True,margin={"top":"0","right":"0","bottom":"0","left":"0"})
            browser.close()
        return target

    def filename(self,session:DebateSession,ext:str)->str:
        return f"{_slug(session.topic)}__{session.session_id}.{ext}"
