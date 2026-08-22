"""Data quality + leakage validation. Produces leakage_report.json content."""

import numpy as np
import pandas as pd


def validate_all(complaints, accounts, atms, transactions, withdrawals, rank_pairs):
    violations = []

    def log(check, mask_or_count, note):
        n = int(mask_or_count.sum()) if hasattr(mask_or_count, "sum") else int(mask_or_count)
        violations.append({"check": check, "violations": n, "note": note})
        return n

    # impossible coordinates
    bad_coords = ~atms["latitude"].between(6, 38) | ~atms["longitude"].between(68, 98)
    log("impossible_atm_coordinates", bad_coords, "ATM lat/lon outside plausible India bounding box")

    bad_vcoords = ~complaints["victim_lat"].between(6, 38) | ~complaints["victim_lon"].between(68, 98)
    log("impossible_victim_coordinates", bad_vcoords, "Victim lat/lon outside plausible India bounding box")

    # negative amounts
    log("negative_reported_loss", (complaints["reported_loss_amount"] < 0), "reported_loss_amount < 0")
    log("negative_transaction_amount", (transactions["amount"] < 0), "transaction amount < 0")
    log("negative_withdrawal_amount", (withdrawals["withdrawal_amount"] < 0), "withdrawal amount < 0")

    # duplicates
    log("duplicate_complaint_ids", complaints["complaint_id"].duplicated(), "duplicate complaint_id")
    log("duplicate_account_ids", accounts["account_id"].duplicated(), "duplicate account_id")
    log("duplicate_atm_ids", atms["atm_id"].duplicated(), "duplicate atm_id")
    log("duplicate_transaction_ids", transactions["transaction_id"].duplicated(), "duplicate transaction_id")
    log("duplicate_withdrawal_ids", withdrawals["withdrawal_id"].duplicated(), "duplicate withdrawal_id")

    # missing IDs
    log("missing_complaint_id_in_transactions", transactions["complaint_id"].isna(), "null complaint_id in transactions")
    log("missing_atm_id_in_withdrawals", withdrawals["atm_id"].isna(), "null atm_id in withdrawals")

    # withdrawal before its own complaint's incident
    wd = withdrawals.merge(complaints[["complaint_id", "incident_timestamp"]], on="complaint_id", how="left")
    before_incident = pd.to_datetime(wd["withdrawal_timestamp"]) < pd.to_datetime(wd["incident_timestamp"])
    log("withdrawal_before_incident", before_incident, "withdrawal_timestamp earlier than incident_timestamp")

    # withdrawal before any transaction of the same complaint
    last_tx = transactions.groupby("complaint_id")["timestamp"].min().rename("first_txn_ts")
    wd2 = withdrawals.merge(last_tx, on="complaint_id", how="left")
    before_first_txn = pd.to_datetime(wd2["withdrawal_timestamp"]) < pd.to_datetime(wd2["first_txn_ts"])
    log("withdrawal_before_first_transaction", before_first_txn.fillna(False), "withdrawal earlier than first transaction in its chain")

    # withdrawal ATM absent from ATM master
    valid_atms = set(atms["atm_id"])
    missing_atm = ~withdrawals["atm_id"].isin(valid_atms)
    log("withdrawal_atm_absent_from_master", missing_atm, "withdrawal.atm_id not present in atm_master")

    # invalid account relationships: from == to
    self_loop = transactions["from_account_id"] == transactions["to_account_id"]
    log("self_loop_transactions", self_loop, "from_account_id == to_account_id")

    # positive ranking label without actual withdrawal match
    if len(rank_pairs):
        true_atm_per_case = withdrawals.set_index("complaint_id")["atm_id"]
        rp = rank_pairs.copy()
        rp["true_atm"] = rp["complaint_id"].map(true_atm_per_case)
        bad_positive = (rp["label"] == 1) & (rp["atm_id"] != rp["true_atm"])
        log("positive_label_without_actual_withdrawal", bad_positive, "label=1 row whose atm_id != the case's actual withdrawal ATM")

        # future information leakage: prediction_timestamp must be < withdrawal_timestamp
        wd_ts_map = withdrawals.set_index("complaint_id")["withdrawal_timestamp"]
        rp["wd_ts"] = rp["complaint_id"].map(wd_ts_map)
        future_leak = pd.to_datetime(rp["prediction_timestamp"]) >= pd.to_datetime(rp["wd_ts"])
        log("prediction_after_or_at_withdrawal", future_leak, "prediction_timestamp >= actual withdrawal_timestamp (label leakage)")

    total_violations = sum(v["violations"] for v in violations)
    report = {
        "total_violations": total_violations,
        "checks": violations,
        "correction_performed": (
            "Rows failing 'withdrawal_before_incident', 'withdrawal_before_first_transaction' or "
            "'prediction_after_or_at_withdrawal' are excluded upstream by construction (the generator "
            "only emits rank_pairs for complaints where prediction_timestamp < withdrawal_timestamp); "
            "any remaining count here indicates a generator bug rather than an already-fixed row."
        ),
    }
    return report
