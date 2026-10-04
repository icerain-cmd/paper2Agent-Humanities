#!/bin/sh
set -eu
APP_ROOT="/home/leeyongwook/p2a-live-agent-debate/skills/paper2agent/paper2humanities"
STATE="/home/leeyongwook/.local/state/paper2agent-humanities"
ENV_FILE="/home/leeyongwook/.config/paper2agent/debate.env"
BACKEND_PID="$STATE/backend.pid"
NGINX_PID="$STATE/nginx/nginx.pid"
LOG="$STATE/logs/backend.log"
PATH="/home/leeyongwook/.local/bin:/home/leeyongwook/.nvm/versions/node/v26.6.0/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export PATH
mkdir -p "$STATE/logs" "$STATE/nginx"
[ -f "$ENV_FILE" ] && set -a && . "$ENV_FILE" && set +a
export PYTHONPATH="$APP_ROOT/src"

alive_pidfile() {
  [ -f "$1" ] || return 1
  pid="$(cat "$1" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

start_backend() {
  if alive_pidfile "$BACKEND_PID"; then return 0; fi
  cd "$APP_ROOT"
  nohup /usr/bin/python3 scripts/serve_debate_api.py --host 127.0.0.1 --port 8765 --model "${P2H_MODEL:-gpt-6-sol}" >>"$LOG" 2>&1 </dev/null &
  echo $! >"$BACKEND_PID"
}

start_nginx() {
  if alive_pidfile "$NGINX_PID"; then return 0; fi
  /usr/sbin/nginx -c /home/leeyongwook/p2a-live-agent-debate/deploy/paper2agent-nginx.conf -p "$STATE/nginx/"
}

stop_all() {
  if alive_pidfile "$NGINX_PID"; then kill "$(cat "$NGINX_PID")" || true; fi
  rm -f "$NGINX_PID"
  if alive_pidfile "$BACKEND_PID"; then kill "$(cat "$BACKEND_PID")" || true; fi
  rm -f "$BACKEND_PID"
}

case "${1:-status}" in
  start)
    start_backend
    i=0
    while [ $i -lt 30 ]; do
      if /usr/bin/curl -fsS http://127.0.0.1:8765/healthz >/dev/null 2>&1; then break; fi
      i=$((i+1)); sleep 1
    done
    start_nginx
    ;;
  stop) stop_all ;;
  restart) stop_all; sleep 1; start_backend; sleep 1; start_nginx ;;
  status)
    if alive_pidfile "$BACKEND_PID"; then echo "backend=RUNNING pid=$(cat "$BACKEND_PID")"; else echo "backend=STOPPED"; fi
    if alive_pidfile "$NGINX_PID"; then echo "nginx=RUNNING pid=$(cat "$NGINX_PID")"; else echo "nginx=STOPPED"; fi
    ;;
  *) echo "usage: $0 {start|stop|restart|status}" >&2; exit 2 ;;
esac
