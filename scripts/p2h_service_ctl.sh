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

pid_matches() {
  file="$1"
  needle="$2"
  [ -f "$file" ] || return 1
  pid="$(cat "$file" 2>/dev/null || true)"
  [ -n "$pid" ] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  cmd="$(tr '\000' ' ' </proc/"$pid"/cmdline 2>/dev/null || true)"
  echo "$cmd" | grep -F "$needle" >/dev/null 2>&1
}

backend_alive() {
  pid_matches "$BACKEND_PID" "serve_debate_api.py" || return 1
  /usr/bin/curl -fsS --max-time 2 http://127.0.0.1:8765/healthz >/dev/null 2>&1
}

nginx_alive() {
  pid_matches "$NGINX_PID" "paper2agent-nginx.conf" || return 1
  /usr/bin/curl -fsS --max-time 2 http://127.0.0.1:8766/healthz >/dev/null 2>&1
}

start_backend() {
  if backend_alive; then return 0; fi
  rm -f "$BACKEND_PID"
  cd "$APP_ROOT"
  nohup /usr/bin/python3 scripts/serve_debate_api.py --host 127.0.0.1 --port 8765 --model "${P2H_MODEL:-gpt-6-sol}" >>"$LOG" 2>&1 </dev/null &
  echo $! >"$BACKEND_PID"
}

start_nginx() {
  if nginx_alive; then return 0; fi
  rm -f "$NGINX_PID"
  /usr/sbin/nginx -c /home/leeyongwook/p2a-live-agent-debate/deploy/paper2agent-nginx.conf -p "$STATE/nginx/"
}

stop_all() {
  if pid_matches "$NGINX_PID" "paper2agent-nginx.conf"; then kill "$(cat "$NGINX_PID")" || true; fi
  rm -f "$NGINX_PID"
  if pid_matches "$BACKEND_PID" "serve_debate_api.py"; then kill "$(cat "$BACKEND_PID")" || true; fi
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
    if backend_alive; then echo "backend=RUNNING pid=$(cat "$BACKEND_PID")"; else echo "backend=STOPPED"; fi
    if nginx_alive; then echo "nginx=RUNNING pid=$(cat "$NGINX_PID")"; else echo "nginx=STOPPED"; fi
    ;;
  *) echo "usage: $0 {start|stop|restart|status}" >&2; exit 2 ;;
esac
