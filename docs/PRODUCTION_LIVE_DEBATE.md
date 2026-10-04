# Paper2Agent-Humanities Live Debate — PC2 Production

## Access

- Local protected URL: `http://localhost:8766/debate`
- Health: `http://localhost:8766/healthz`
- Owner username: `leeyongwook`
- Owner password is stored only on PC2 in:
  `/home/leeyongwook/.config/paper2agent/debate.env`
- The reverse proxy listens on `127.0.0.1` only. Do not expose port 8766 to an untrusted network without TLS.

## Processes

Backend:

- FastAPI/Uvicorn on `127.0.0.1:8765`
- model runtime: Codex CLI, default `gpt-6-sol`

Reverse proxy:

- dedicated nginx instance on `127.0.0.1:8766`
- config: `deploy/paper2agent-nginx.conf`
- does not modify or share the DeerFlow nginx instance on port 2026

## Persistent data

Production data is outside Git worktrees:

`/home/leeyongwook/.local/share/paper2agent-humanities`

It contains:

- `paper2humanities.db` — persistent debate sessions/events
- `active/` — registered agents
- `disabled/` — disabled registered agents
- `sources/` — source PDFs keyed by SHA-256
- `pdf_jobs/` and `staging/` — onboarding state

## Session recovery

- completed sessions survive process/WSL restarts
- sessions found in `RUNNING` state at server startup become `INTERRUPTED`
- interrupted sessions are never automatically resumed
- the web UI shows a **Resume** action under Recent Sessions
- Resume continues from the last committed turn
- SSE uses event IDs and `Last-Event-ID` to avoid event replay on reconnect

## Service control

```bash
/home/leeyongwook/p2a-live-agent-debate/scripts/p2h_service_ctl.sh status
/home/leeyongwook/p2a-live-agent-debate/scripts/p2h_service_ctl.sh start
/home/leeyongwook/p2a-live-agent-debate/scripts/p2h_service_ctl.sh stop
/home/leeyongwook/p2a-live-agent-debate/scripts/p2h_service_ctl.sh restart
```

## Auto-start

A systemd unit is installed at:

`/etc/systemd/system/paper2agent-debate.service`

PC2's current WSL environment reports systemd as offline. Therefore the active boot mechanism is the existing WSL boot hook:

`/usr/local/sbin/wsl-boot-services.sh`

The Paper2Agent start command was added before the existing `exit 0`. Existing SSH and NAS boot commands were preserved.

A backup of the pre-Paper2Agent boot script was created during installation.

## Logs

`/home/leeyongwook/.local/state/paper2agent-humanities/logs`

- `backend.log`
- `nginx-access.log`
- `nginx-error.log`

Logrotate policy:

`/etc/logrotate.d/paper2agent-humanities`

Daily, 7 rotations, compressed.

## Health contract

`GET /healthz` is intentionally unauthenticated and returns:

- registry status
- DB status
- session counts
- model runtime availability
- active runner count

All other production routes require HTTP Basic authentication when `P2H_AUTH_USER` and `P2H_AUTH_PASSWORD` are configured.

## Recovery

If the UI is unreachable:

1. Check service state:
   `p2h_service_ctl.sh status`
2. Check `http://localhost:8766/healthz`
3. Inspect `backend.log` and `nginx-error.log`
4. Run `p2h_service_ctl.sh restart`
5. Do not delete the persistent data directory during code rollback.

## Verification completed

Productionization verification included:

- SQLite session round-trip
- RUNNING -> INTERRUPTED restart recovery
- browser Resume -> completed live debate
- concurrent session isolation
- SSE Last-Event-ID replay protection
- owner authentication
- localhost reverse proxy
- persistent logs
- WSL cold restart auto-start
- browser access and persisted session visibility after cold restart
