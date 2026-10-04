# Paper2Agent-Humanities Secure Remote Access

## Endpoint

Paper2Agent-Humanities is exposed only inside the owner's Tailscale tailnet.

- Remote HTTPS endpoint:
  `https://lab-pc2.taile8e20d.ts.net:8443/`
- Health:
  `https://lab-pc2.taile8e20d.ts.net:8443/healthz`
- Debate UI:
  `https://lab-pc2.taile8e20d.ts.net:8443/debate`

The endpoint is **tailnet only**. Tailscale Funnel is not enabled.

## Topology

```text
iPhone / PC1 / other authorized tailnet device
        |
     Tailscale HTTPS
        |
lab-pc2.taile8e20d.ts.net:8443
        |
Tailscale Serve
        |
http://127.0.0.1:8766
        |
dedicated Paper2Agent nginx
        |
http://127.0.0.1:8765
        |
FastAPI / Live Debate
```

## Existing Serve preserved

Before Milestone 8:

```text
https://lab-pc2.taile8e20d.ts.net/
  -> http://127.0.0.1:17640
```

After Milestone 8:

```text
https://lab-pc2.taile8e20d.ts.net/
  -> http://127.0.0.1:17640

https://lab-pc2.taile8e20d.ts.net:8443/
  -> http://127.0.0.1:8766
```

The original root service was not modified.

## Authentication

Two independent access boundaries are active:

1. Tailscale tailnet membership
2. Paper2Agent HTTP Basic authentication

The Paper2Agent owner credential is stored only on PC2:

`/home/leeyongwook/.config/paper2agent/debate.env`

Do not commit this file.

## Tailscale state backup

Local Windows backups created before/after configuration:

```text
C:\Temp\p2h\tailscale-serve-backup-20261004.json
C:\Temp\p2h\tailscale-serve-status-before.txt
C:\Temp\p2h\tailscale-serve-status-after.txt
C:\Temp\p2h\tailscale-funnel-status-after.txt
```

The current Tailscale version returns only a version object from
`serve get-config --all` for this legacy-style Serve configuration, so the textual
`serve status` files are the authoritative rollback reference.

## Rollback

Disable only the Paper2Agent listener:

```powershell
tailscale serve --https=8443 off
```

Then verify the existing root service remains:

```powershell
tailscale serve status
```

Expected remaining root:

```text
https://lab-pc2.taile8e20d.ts.net/
|-- / proxy http://127.0.0.1:17640
```

To recreate Paper2Agent remote access:

```powershell
tailscale serve --bg --https=8443 http://127.0.0.1:8766
```

## Verification completed

- Existing Tailscale root service unchanged: PASS
- Paper2Agent HTTPS endpoint: PASS
- TLS verification through Windows networking: PASS
- `/healthz`: 200
- unauthenticated `/debate`: 401
- owner-authenticated `/debate`: 200
- UI content returned: PASS
- iPhone tailnet connectivity: PASS via Tailscale ping
- PC1 tailnet connectivity: PASS via direct Tailscale ping
- non-tailnet remote host could not resolve the MagicDNS hostname
- WSL cold restart -> Paper2Agent backend/proxy auto-start: PASS
- WSL cold restart -> Tailscale HTTPS endpoint recovery: PASS
- Tailscale status reports both services as `tailnet only`
- Funnel was not enabled

## Device notes

At verification time:

- PC2: `lab-pc2`
- iPhone: `iphone-11`
- PC1: `lab-pc1`

The iPhone and PC1 were confirmed reachable on the same tailnet. Browser automation
was available only on PC2, so interactive browser rendering on those two physical
devices was not remotely automated during this milestone.

## Security rule

Do not replace Tailscale Serve with Funnel for this service unless public internet
exposure is explicitly approved in a separate design review.
