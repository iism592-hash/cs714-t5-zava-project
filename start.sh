#!/bin/bash
set -euo pipefail
if [ "${APP_TYPE:-B2C}" = "B2B" ]; then
    exec python -m streamlit run src/python/b2b_app/app.py --server.port 8000 --server.address 0.0.0.0
fi
pids=()
cleanup() {
    trap - EXIT TERM INT
    if ((${#pids[@]} > 0)); then kill "${pids[@]}" 2>/dev/null || true; fi
    wait || true
}
trap cleanup EXIT TERM INT
python src/python/mcp_server/customer_sales/customer_sales.py --host 127.0.0.1 --port 8000 &
pids+=($!)
python src/python/services/agent_service.py &
pids+=($!)
python src/python/web_app/web_app.py &
pids+=($!)
# Wait for the web interface before declaring startup successful.
ready=0
for attempt in {1..30}; do
    for pid in "${pids[@]}"; do
        kill -0 "$pid" 2>/dev/null || exit 1
    done
    if curl --fail --silent --max-time 2 "http://127.0.0.1:${PORT:-8005}/health" >/dev/null; then
        ready=1
        break
    fi
    sleep 1
done
if ((ready == 0)); then echo 'Web startup health check failed' >&2; exit 1; fi
# Any service exit terminates the container so the host can restart it.
set +e
wait -n "${pids[@]}"
status=$?
set -e
exit "$status"
