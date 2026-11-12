"""
sanjeevani/audit.py
-------------------
Member 4: Tamper-Evident SHA-256 Hash-Chained Audit Log Module.
Records system-level events across all 8 operational categories:
  1. Emergency report received
  2. Incident verified
  3. Road failure simulated
  4. Risk assessment generated
  5. Future scenario generated
  6. Rescue route recalculated
  7. Emergency resource assigned
  8. Final response status
Uses timestamps and cryptographic SHA-256 hash chaining (not a blockchain).
"""

from datetime import datetime
import hashlib
import pandas as pd


GENESIS_HASH = "0" * 64


def compute_entry_hash(
    timestamp: str,
    stage: str,
    action_type: str,
    details: str,
    prev_hash: str,
) -> str:
    """Compute a deterministic SHA-256 digest linking the current entry to prev_hash."""
    payload = f"{timestamp}|{stage}|{action_type}|{details}|{prev_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_initial_audit_log() -> list[dict]:
    """Create the initial baseline synthetic audit log covering all 8 core operational event types."""
    seed_events = [
        (
            "17:42:30",
            "OBSERVE",
            "Emergency Report Received",
            "INC-901 ingested at Sector 4 Underpass (Urgency: CRITICAL, Confidence: 94%)",
        ),
        (
            "17:45:10",
            "VERIFY",
            "Incident Verified",
            "INC-901 verified with unique flood image signature (Confidence: 94%); INC-905 held for duplicate review",
        ),
        (
            "17:47:05",
            "ESTIMATE",
            "Road Failure Simulated",
            "RD-103 (Sector 4 Underpass Link) marked BLOCKED due to 2.1m simulated water depth",
        ),
        (
            "17:48:40",
            "ESTIMATE",
            "Risk Assessment Generated",
            "Evaluated NetworkX road vulnerability scores (RD-103: 95/100, RD-101: 88/100) and hospital reachability",
        ),
        (
            "17:50:19",
            "SIMULATE",
            "Future Scenario Generated",
            "Digital Twin evaluated T+15m, T+30m, and T+60m flood projections for Riverfront Arterial Bridge",
        ),
        (
            "17:52:08",
            "OPTIMIZE",
            "Rescue Route Recalculated",
            "NetworkX recalculated shortest safe corridor around blocked RD-103 via RD-105 & RD-108",
        ),
        (
            "17:53:42",
            "OPTIMIZE",
            "Emergency Resource Assigned",
            "Assigned RESCUE-ALPHA to INC-901 and AMB-104 to INC-903 under Strategy C (Risk-Aware Response)",
        ),
        (
            "17:55:15",
            "REPEAT",
            "Final Response Status",
            "Closed-loop cycle complete: 4 verified incidents dispatched on passable corridors; 1 duplicate held",
        ),
    ]

    entries: list[dict] = []
    prev_hash = GENESIS_HASH
    for idx, (ts, stage, action_type, details) in enumerate(seed_events, start=1):
        entry_hash = compute_entry_hash(ts, stage, action_type, details, prev_hash)
        entries.append(
            {
                "event_id": f"AUD-{idx:03d}",
                "timestamp": ts,
                "stage": stage,
                "action_type": action_type,
                "details": details,
                "prev_hash": prev_hash[:12] + "...",
                "entry_hash": entry_hash[:16] + "...",
                "full_prev_hash": prev_hash,
                "full_entry_hash": entry_hash,
            }
        )
        prev_hash = entry_hash

    return entries


def append_audit_event(
    audit_list: list[dict],
    stage: str,
    action_type: str,
    details: str,
) -> list[dict]:
    """Append a new timestamped, SHA-256 hash-chained event to the session audit log."""
    if not isinstance(audit_list, list):
        audit_list = create_initial_audit_log()

    prev_hash = (
        audit_list[-1]["full_entry_hash"] if len(audit_list) > 0 else GENESIS_HASH
    )
    now_str = datetime.now().strftime("%H:%M:%S")
    entry_hash = compute_entry_hash(now_str, stage, action_type, details, prev_hash)
    next_id = f"AUD-{len(audit_list) + 1:03d}"

    audit_list.append(
        {
            "event_id": next_id,
            "timestamp": now_str,
            "stage": stage,
            "action_type": action_type,
            "details": details,
            "prev_hash": prev_hash[:12] + "...",
            "entry_hash": entry_hash[:16] + "...",
            "full_prev_hash": prev_hash,
            "full_entry_hash": entry_hash,
        }
    )
    return audit_list


def verify_audit_chain_detailed(audit_list: list[dict]) -> dict:
    """
    Recalculate the SHA-256 hash chain across every audit entry and return:
      - overall_valid (bool)
      - status_label ("VERIFIED" or "INTEGRITY FAILURE")
      - summary_message (str)
      - entry_results (list of dicts with per-entry Verification Status)
    """
    if not audit_list:
        return {
            "overall_valid": True,
            "status_label": "VERIFIED",
            "summary_message": "Audit log is empty (0 entries).",
            "entry_results": [],
            "failed_event_ids": [],
        }

    expected_prev = GENESIS_HASH
    overall_valid = True
    first_failure_msg = ""
    failed_ids = []
    entry_results = []
    chain_broken_upstream = False

    for idx, item in enumerate(audit_list):
        ev_id = item.get("event_id", f"AUD-{idx + 1:03d}")
        stored_prev = item.get("full_prev_hash", "")
        stored_curr = item.get("full_entry_hash", "")

        recalc_curr = compute_entry_hash(
            item["timestamp"],
            item["stage"],
            item["action_type"],
            item["details"],
            expected_prev,
        )

        prev_ok = stored_prev == expected_prev
        curr_ok = stored_curr == recalc_curr

        if prev_ok and curr_ok and not chain_broken_upstream:
            v_status = "✅ VERIFIED"
        else:
            overall_valid = False
            failed_ids.append(ev_id)
            if not curr_ok and prev_ok:
                v_status = "🚨 INTEGRITY FAILURE (Tampered Payload)"
                if not first_failure_msg:
                    first_failure_msg = (
                        f"INTEGRITY FAILURE detected at {ev_id} (entry #{idx + 1}): "
                        "Recalculated SHA-256 digest does not match stored hash."
                    )
            else:
                v_status = "❌ CHAIN BROKEN (Upstream Hash Mismatch)"
                if not first_failure_msg:
                    first_failure_msg = (
                        f"INTEGRITY FAILURE detected at {ev_id} (entry #{idx + 1}): "
                        "Previous hash link broken."
                    )
            chain_broken_upstream = True

        entry_results.append(
            {
                "Event ID": ev_id,
                "Event Type": item["action_type"],
                "Stage": item["stage"],
                "Timestamp": item["timestamp"],
                "Event Description": item["details"],
                "Previous Hash": item["prev_hash"],
                "Current Hash": item["entry_hash"],
                "Verification Status": v_status,
                # Keep aliases for Section 1 backward compatibility
                "Action": item["action_type"],
                "Details": item["details"],
                "Prev Hash": item["prev_hash"],
                "SHA-256 Digest": item["entry_hash"],
            }
        )
        # Advance expected_prev using recalculated hash so downstream breakage is also flagged
        expected_prev = recalc_curr

    if overall_valid:
        summary_msg = f"VERIFIED: All {len(audit_list)} SHA-256 hash-chained audit entries are intact."
    else:
        summary_msg = first_failure_msg

    return {
        "overall_valid": overall_valid,
        "status_label": "VERIFIED" if overall_valid else "INTEGRITY FAILURE",
        "summary_message": summary_msg,
        "entry_results": entry_results,
        "failed_event_ids": failed_ids,
    }


def verify_audit_chain(audit_list: list[dict]) -> tuple[bool, str]:
    """Verify the SHA-256 hash chain integrity across all recorded audit entries."""
    res = verify_audit_chain_detailed(audit_list)
    if not res["overall_valid"]:
        return False, res["summary_message"]
    return True, f"Verified {len(audit_list)} chained entries (SHA-256 integrity intact)."


def get_audit_dataframe(audit_list: list[dict]) -> pd.DataFrame:
    """Return a clean user-facing DataFrame (newest first) with per-entry SHA-256 verification status."""
    detailed = verify_audit_chain_detailed(audit_list)
    if not detailed["entry_results"]:
        return pd.DataFrame(
            columns=[
                "Event ID",
                "Event Type",
                "Stage",
                "Timestamp",
                "Event Description",
                "Previous Hash",
                "Current Hash",
                "Verification Status",
                "Action",
                "Details",
                "Prev Hash",
                "SHA-256 Digest",
            ]
        )
    return pd.DataFrame(list(reversed(detailed["entry_results"])))
