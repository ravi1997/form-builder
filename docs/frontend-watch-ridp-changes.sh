#!/usr/bin/env bash
set -uo pipefail

FRONTEND_REPO="${FRONTEND_REPO:-/home/ravi/workspace/frontend}"
BACKEND_REPO="${BACKEND_REPO:-/home/ravi/workspace/docker/apps/form-backend}"
LOG_ROOT="${LOG_ROOT:-/home/ravi/workspace/.agent-worker-logs}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-15}"
DEBOUNCE_SECONDS="${DEBOUNCE_SECONDS:-25}"
AUTO_COMMIT="${AUTO_COMMIT:-0}"
REPORT_ONLY="${REPORT_ONLY:-1}"
FULL_FRONTEND="${FULL_FRONTEND:-1}"
FULL_BACKEND="${FULL_BACKEND:-1}"
RUN_ON_START="${RUN_ON_START:-1}"

mkdir -p "$LOG_ROOT"

signature() {
  local repo="$1"
  {
    git -C "$repo" status --porcelain=v1
    git -C "$repo" diff --binary
    git -C "$repo" diff --cached --binary
    git -C "$repo" ls-files --others --exclude-standard -z |
      while IFS= read -r -d '' file; do
        printf 'untracked:%s\n' "$file"
        sha256sum "$repo/$file" 2>/dev/null || true
      done || true
  } | sha256sum | awk '{print $1}'
}

changed_files() {
  local repo="$1"
  git -C "$repo" status --porcelain=v1 | sed 's/^...//' | sort
}

run_logged() {
  local repo="$1"
  local log="$2"
  shift 2
  {
    printf '\n### %s\n' "$*"
    printf '$ cd %s && %s\n' "$repo" "$*"
  } >> "$log"
  (cd "$repo" && "$@") >> "$log" 2>&1
}

has_changes() {
  local repo="$1"
  [ -n "$(git -C "$repo" status --porcelain=v1)" ]
}

commit_if_clean_checks_passed() {
  local repo="$1"
  local label="$2"
  local log="$3"

  if [ "$REPORT_ONLY" = "1" ] || [ "$AUTO_COMMIT" != "1" ] || ! has_changes "$repo"; then
    return 0
  fi

  git -C "$repo" add -A >> "$log" 2>&1
  if git -C "$repo" diff --cached --quiet; then
    return 0
  fi

  local subject="chore(${label}): verify agent changes"
  git -C "$repo" commit -m "$subject" >> "$log" 2>&1
}

check_frontend() {
  local log="$1"
  local files="$2"

  if ! grep -Eq '^(lib/|test/|pubspec\.yaml|analysis_options\.yaml|web/|assets/|AGENTS\.md|\.agents/|\.mcp\.json|\.kilo/)' <<<"$files"; then
    printf '\nNo frontend code/test/tooling files changed; skipping Flutter gates.\n' >> "$log"
    return 0
  fi

  run_logged "$FRONTEND_REPO" "$log" flutter analyze
  if [ "$FULL_FRONTEND" = "1" ]; then
    run_logged "$FRONTEND_REPO" "$log" flutter test
  fi
}

check_backend() {
  local log="$1"
  local files="$2"

  if ! grep -Eq '^((app|extensions)\.py|models/|schemas/|routes/|services/|tasks/|middleware/|utils/|tests/|workers/|config/|AGENTS\.md|\.agents/|\.mcp\.json)' <<<"$files"; then
    printf '\nNo backend code/test/tooling files changed; skipping backend gates.\n' >> "$log"
    return 0
  fi

  if [ "$FULL_BACKEND" = "1" ]; then
    run_logged "$BACKEND_REPO" "$log" make test
  else
    run_logged "$BACKEND_REPO" "$log" python3 -m compileall app.py models schemas routes services tasks middleware utils workers
  fi

  if grep -Eq '^(routes/|schemas/|models/|services/|tests/test_openapi|docs/openapi|docs/swagger)' <<<"$files" &&
    [ -f "$BACKEND_REPO/tests/test_openapi_contract.py" ]; then
    run_logged "$BACKEND_REPO" "$log" docker compose run --rm backend pytest tests/test_openapi_contract.py -q
  fi
}

security_checks() {
  local repo="$1"
  local log="$2"
  if command -v gitleaks >/dev/null 2>&1; then
    run_logged "$repo" "$log" gitleaks detect --source . --no-git --redact
  fi
}

process_changes() {
  local ts log frontend_files backend_files
  ts="$(date +%Y%m%d-%H%M%S)"
  log="$LOG_ROOT/run-$ts.md"
  frontend_files="$(changed_files "$FRONTEND_REPO")"
  backend_files="$(changed_files "$BACKEND_REPO")"

  {
    printf '# RIDP Agent Worker Run %s\n\n' "$ts"
    printf '## Frontend changes\n```text\n%s\n```\n\n' "$frontend_files"
    printf '## Backend changes\n```text\n%s\n```\n\n' "$backend_files"
  } > "$log"

  local ok=1
  if has_changes "$FRONTEND_REPO"; then
    check_frontend "$log" "$frontend_files" || ok=0
    security_checks "$FRONTEND_REPO" "$log" || ok=0
  fi
  if has_changes "$BACKEND_REPO"; then
    check_backend "$log" "$backend_files" || ok=0
    security_checks "$BACKEND_REPO" "$log" || ok=0
  fi

  if [ "$ok" = "1" ]; then
    printf '\n## Result\nChecks passed. Report-only mode made no repository changes.\n' >> "$log"
    commit_if_clean_checks_passed "$FRONTEND_REPO" "frontend" "$log"
    commit_if_clean_checks_passed "$BACKEND_REPO" "backend" "$log"
  else
    printf '\n## Result\nIssues found. Report-only mode made no repository changes.\n' >> "$log"
  fi

  printf '%s\n' "$log" > "$LOG_ROOT/latest"
  printf '[%s] processed changes: %s\n' "$(date --iso-8601=seconds)" "$log"
}

main() {
  printf '[%s] RIDP watcher started\n' "$(date --iso-8601=seconds)"
  printf 'frontend=%s\nbackend=%s\nlogs=%s\nreport_only=%s\nauto_commit=%s\n' "$FRONTEND_REPO" "$BACKEND_REPO" "$LOG_ROOT" "$REPORT_ONLY" "$AUTO_COMMIT"

  local last_sig current_sig stable_sig
  last_sig="$(signature "$FRONTEND_REPO")-$(signature "$BACKEND_REPO")"

  if [ "$RUN_ON_START" = "1" ] && { has_changes "$FRONTEND_REPO" || has_changes "$BACKEND_REPO"; }; then
    printf '[%s] existing changes detected; debouncing %ss\n' "$(date --iso-8601=seconds)" "$DEBOUNCE_SECONDS"
    sleep "$DEBOUNCE_SECONDS"
    process_changes || true
    last_sig="$(signature "$FRONTEND_REPO")-$(signature "$BACKEND_REPO")"
  fi

  while true; do
    sleep "$INTERVAL_SECONDS"
    current_sig="$(signature "$FRONTEND_REPO")-$(signature "$BACKEND_REPO")"
    if [ "$current_sig" = "$last_sig" ]; then
      continue
    fi

    printf '[%s] change detected; debouncing %ss\n' "$(date --iso-8601=seconds)" "$DEBOUNCE_SECONDS"
    sleep "$DEBOUNCE_SECONDS"
    stable_sig="$(signature "$FRONTEND_REPO")-$(signature "$BACKEND_REPO")"
    if [ "$stable_sig" != "$current_sig" ]; then
      printf '[%s] changes still moving; waiting\n' "$(date --iso-8601=seconds)"
      last_sig="$stable_sig"
      continue
    fi

    process_changes || true
    last_sig="$(signature "$FRONTEND_REPO")-$(signature "$BACKEND_REPO")"
  done
}

main "$@"
