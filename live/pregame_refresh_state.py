"""Pure state transitions for bounded pregame odds refresh attempts."""

MAX_PRIMARY_ATTEMPTS = 2
MONTHLY_PRIMARY_REQUEST_CAP = 125
PRIMARY_PROVIDERS = ("game", "player")

def reserved_attempt(state, ledger_entries, keys, timestamp):
    state = dict(state)
    attempts = dict(state.get("attempts", {}))
    completed = set(state.get("slates", []))
    failed = set(state.get("failed_slates", []))
    pending = [key for key in keys if key not in completed and key not in failed]
    if not pending:
        return state, ledger_entries, [], None
    status = {key: dict(value) for key, value in state.get("provider_success", {}).items()}
    requested = {provider for key in pending for provider in PRIMARY_PROVIDERS if not status.get(key, {}).get(provider, False)}
    if not requested:
        state["slates"] = sorted(completed | set(pending))
        state["provider_success"] = status
        return state, 0, [], None
    if MONTHLY_PRIMARY_REQUEST_CAP - ledger_entries < len(requested):
        state["failed_slates"] = sorted(failed | set(pending))
        state["failures"] = {**state.get("failures", {}), **{key: "monthly primary API cap exhausted" for key in pending}}
        return state, ledger_entries, pending, "budget_exhausted"
    attempt = max((int(attempts.get(key, 0)) for key in pending), default=0) + 1
    if attempt > MAX_PRIMARY_ATTEMPTS:
        state["failed_slates"] = sorted(failed | set(pending))
        return state, ledger_entries, pending, "attempts_exhausted"
    for key in pending:
        attempts[key] = attempt
    state["attempts"] = attempts
    state["provider_success"] = status
    state["last_attempt_at_utc"] = timestamp
    return state, len(requested), pending, (attempt, requested)

def record_result(state, keys, attempt, results, backup_ok, failure_reason=None):
    state = dict(state)
    completed = set(state.get("slates", []))
    failed = set(state.get("failed_slates", []))
    failures = dict(state.get("failures", {}))
    status = {key: dict(value) for key, value in state.get("provider_success", {}).items()}
    for key in keys:
        for provider, succeeded in results.items():
            status.setdefault(key, {})[provider] = bool(succeeded or status.get(key, {}).get(provider, False))
        if all(status.get(key, {}).get(provider, False) for provider in PRIMARY_PROVIDERS):
            completed.add(key)
            failed.discard(key)
            failures.pop(key, None)
        elif attempt >= MAX_PRIMARY_ATTEMPTS:
            failed.add(key)
            failures[key] = failure_reason or "primary provider failed twice"
    state["provider_success"] = status
    state["slates"] = sorted(completed)
    state["failed_slates"] = sorted(failed)
    state["failures"] = failures
    state["last_attempt_result"] = "primary_success" if all(results.get(p, False) or all(status.get(k, {}).get(p, False) for k in keys) for p in PRIMARY_PROVIDERS) else "primary_failed"
    state["last_backup_result"] = "success" if backup_ok else "failed"
    return state
