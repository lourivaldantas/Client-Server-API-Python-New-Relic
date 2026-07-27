#!/usr/bin/env bash

set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8001}"
CONCURRENCY="${CONCURRENCY:-5}"
REQUEST_INTERVAL="${REQUEST_INTERVAL:-0.1}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-15}"
ERROR_RATE="${ERROR_RATE:-3}"
ROOT_RATE="${ROOT_RATE:-10}"

request_count=0
active_pids=()

stop_script() {
    if ((${#active_pids[@]} > 0)); then
        kill "${active_pids[@]}" 2>/dev/null || true
        wait "${active_pids[@]}" 2>/dev/null || true
    fi

    printf '\nTráfego encerrado após %d requisições enviadas.\n' "$request_count"
    exit 0
}

trap stop_script INT TERM

validate_percentage() {
    local name="$1"
    local value="$2"

    if [[ ! "$value" =~ ^[0-9]+$ ]] || ((value < 0 || value > 100)); then
        printf '%s deve ser um número inteiro entre 0 e 100.\n' "$name" >&2
        exit 1
    fi
}

if [[ ! "$CONCURRENCY" =~ ^[1-9][0-9]*$ ]]; then
    printf 'CONCURRENCY deve ser um número inteiro maior que zero.\n' >&2
    exit 1
fi

validate_percentage "ERROR_RATE" "$ERROR_RATE"
validate_percentage "ROOT_RATE" "$ROOT_RATE"

if ((ERROR_RATE + ROOT_RATE > 100)); then
    printf 'A soma de ERROR_RATE e ROOT_RATE não pode ultrapassar 100.\n' >&2
    exit 1
fi

send_request() {
    local request_number="$1"
    local method="$2"
    local url="$3"
    local request_type="$4"
    local timestamp
    local result
    local curl_status
    local http_status
    local elapsed_time

    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"

    result="$(
        curl \
            --request "$method" \
            --silent \
            --show-error \
            --output /dev/null \
            --write-out '%{http_code} %{time_total}' \
            --max-time "$REQUEST_TIMEOUT" \
            "$url" 2>&1
    )"
    curl_status=$?

    if ((curl_status == 0)); then
        http_status="${result%% *}"
        elapsed_time="${result#* }"
        printf '[%s] #%d %-9s %s %s → HTTP %s em %ss\n' \
            "$timestamp" \
            "$request_number" \
            "$request_type" \
            "$method" \
            "$url" \
            "$http_status" \
            "$elapsed_time"
    else
        printf '[%s] #%d %-9s %s %s → falhou: %s\n' \
            "$timestamp" \
            "$request_number" \
            "$request_type" \
            "$method" \
            "$url" \
            "$result" >&2
    fi
}

printf 'Enviando tráfego continuamente para %s\n' "$BASE_URL"
printf 'Concorrência: %s | Intervalo por lote: %ss | Timeout: %ss\n' \
    "$CONCURRENCY" \
    "$REQUEST_INTERVAL" \
    "$REQUEST_TIMEOUT"
printf 'Distribuição: %s%% erros | %s%% health checks | %s%% fluxo completo\n' \
    "$ERROR_RATE" \
    "$ROOT_RATE" \
    "$((100 - ERROR_RATE - ROOT_RATE))"
printf 'Encerre com Ctrl+C\n\n'

while :; do
    active_pids=()

    for ((batch_count = 0; batch_count < CONCURRENCY; batch_count++)); do
        request_count=$((request_count + 1))
        roll=$((RANDOM % 100))

        if ((roll < ERROR_RATE)); then
            if ((RANDOM % 2 == 0)); then
                method="GET"
                url="${BASE_URL}/rota-inexistente-$RANDOM"
                request_type="erro-404"
            else
                method="POST"
                url="${BASE_URL}/users"
                request_type="erro-405"
            fi
        elif ((roll < ERROR_RATE + ROOT_RATE)); then
            method="GET"
            url="${BASE_URL}/"
            request_type="health"
        else
            method="GET"
            url="${BASE_URL}/users"
            request_type="fluxo"
        fi

        send_request "$request_count" "$method" "$url" "$request_type" &
        active_pids+=("$!")
    done

    for pid in "${active_pids[@]}"; do
        wait "$pid" || true
    done

    active_pids=()
    sleep "$REQUEST_INTERVAL"
done
