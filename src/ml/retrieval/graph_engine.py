"""
Temporal Graph Engine for Mule Network and Financial Flow Analytics.

Constructs directed transaction graphs from historical edges and provides
strict point-in-time (t <= T) ego-network extraction, degree centralities,
shared UPI resolution, and mule-linked ATM identification.
"""

import pandas as pd
import networkx as nx
from datetime import datetime
from typing import Dict, Any, List, Set, Optional, Tuple


class TemporalGraphEngine:
    """
    Manages transaction graphs with timestamp awareness.
    Guarantees no future graph edges are traversed when querying features as of time T.
    """

    def __init__(
        self,
        graph_edges_df: Optional[pd.DataFrame] = None,
        accounts_df: Optional[pd.DataFrame] = None,
        upi_df: Optional[pd.DataFrame] = None,
        case_links_df: Optional[pd.DataFrame] = None,
        withdrawals_df: Optional[pd.DataFrame] = None,
    ):
        self.raw_edges = graph_edges_df.copy() if graph_edges_df is not None else pd.DataFrame()
        self.accounts_df = accounts_df.copy() if accounts_df is not None else pd.DataFrame()
        self.upi_df = upi_df.copy() if upi_df is not None else pd.DataFrame()
        self.case_links_df = case_links_df.copy() if case_links_df is not None else pd.DataFrame()
        self.withdrawals_df = withdrawals_df.copy() if withdrawals_df is not None else pd.DataFrame()

        self._normalize_timestamps()
        self._build_upi_mappings()
        self._build_case_cluster_mappings()

    def _normalize_timestamps(self) -> None:
        if not self.raw_edges.empty and "timestamp" in self.raw_edges.columns:
            self.raw_edges["ts"] = pd.to_datetime(self.raw_edges["timestamp"], errors="coerce")
        if not self.withdrawals_df.empty and "withdrawal_timestamp" in self.withdrawals_df.columns:
            self.withdrawals_df["ts"] = pd.to_datetime(self.withdrawals_df["withdrawal_timestamp"], errors="coerce")

    def _build_upi_mappings(self) -> None:
        """Map UPI IDs to account IDs and vice versa."""
        self.upi_to_accounts: Dict[str, Set[str]] = {}
        self.account_to_upis: Dict[str, Set[str]] = {}

        if not self.upi_df.empty and "upi_id" in self.upi_df.columns and "account_id" in self.upi_df.columns:
            for _, row in self.upi_df.iterrows():
                u, a = str(row["upi_id"]).strip(), str(row["account_id"]).strip()
                if u and a:
                    self.upi_to_accounts.setdefault(u, set()).add(a)
                    self.account_to_upis.setdefault(a, set()).add(u)

    def _build_case_cluster_mappings(self) -> None:
        """Map complaint IDs to fraud cluster IDs and chain accounts."""
        self.case_to_cluster: Dict[str, str] = {}
        self.case_to_chain: Dict[str, List[str]] = {}
        self.case_to_cashout_acc: Dict[str, str] = {}

        if not self.case_links_df.empty:
            for _, row in self.case_links_df.iterrows():
                cid = str(row.get("complaint_id", "")).strip()
                if not cid:
                    continue
                self.case_to_cluster[cid] = str(row.get("cluster_id", "none")).strip()
                self.case_to_cashout_acc[cid] = str(row.get("cashout_account_id", "")).strip()
                raw_chain = str(row.get("chain_accounts", "")).strip()
                self.case_to_chain[cid] = [a.strip() for a in raw_chain.split("|") if a.strip()]

    def get_subgraph_as_of_T(self, as_of_T: datetime) -> nx.DiGraph:
        """
        Extract directed transaction graph containing strictly edges where timestamp <= as_of_T.
        """
        if self.raw_edges.empty:
            return nx.DiGraph()

        edges_t = self.raw_edges[self.raw_edges["ts"] <= as_of_T]
        G = nx.DiGraph()
        if edges_t.empty:
            return G

        srcs = edges_t["src_account_id"].values
        dsts = edges_t["dst_account_id"].values
        amts = edges_t["amount"].values if "amount" in edges_t.columns else np.zeros(len(edges_t))
        cids = edges_t["complaint_id"].values if "complaint_id" in edges_t.columns else np.full(len(edges_t), "")

        for u, v, amt, cid in zip(srcs, dsts, amts, cids):
            u_str = str(u).strip()
            v_str = str(v).strip()
            cid_str = str(cid).strip()

            if G.has_edge(u_str, v_str):
                ed = G[u_str][v_str]
                ed["weight"] += float(amt)
                ed["count"] += 1
                ed["cases"].add(cid_str)
            else:
                G.add_edge(u_str, v_str, weight=float(amt), count=1, cases={cid_str})
        return G

    def get_account_graph_features_as_of_T(self, account_id: str, as_of_T: datetime) -> Dict[str, float]:
        """
        Compute point-in-time graph metrics for an account as of timestamp T.
        """
        G = self.get_subgraph_as_of_T(as_of_T)
        acc = str(account_id).strip()

        if not G.has_node(acc):
            return {
                "account_degree_as_of_T": 0.0,
                "in_degree_as_of_T": 0.0,
                "out_degree_as_of_T": 0.0,
                "weighted_degree_as_of_T": 0.0,
                "cluster_size": 1.0,
                "linked_complaint_count_as_of_T": 0.0,
            }

        in_deg = G.in_degree(acc)
        out_deg = G.out_degree(acc)
        total_deg = in_deg + out_deg

        in_weight = sum(d.get("weight", 0.0) for _, _, d in G.in_edges(acc, data=True))
        out_weight = sum(d.get("weight", 0.0) for _, _, d in G.out_edges(acc, data=True))

        # Linked complaints in 1-hop ego network
        linked_cases = set()
        for _, _, d in G.in_edges(acc, data=True):
            linked_cases.update(d.get("cases", set()))
        for _, _, d in G.out_edges(acc, data=True):
            linked_cases.update(d.get("cases", set()))
        linked_cases.discard("")

        # Ego net size
        ego_nodes = set(nx.ego_graph(G, acc, radius=1, undirected=True).nodes())

        return {
            "account_degree_as_of_T": float(total_deg),
            "in_degree_as_of_T": float(in_deg),
            "out_degree_as_of_T": float(out_deg),
            "weighted_degree_as_of_T": float(in_weight + out_weight),
            "cluster_size": float(len(ego_nodes)),
            "linked_complaint_count_as_of_T": float(len(linked_cases)),
        }

    def get_network_associated_atms_as_of_T(self, chain_accounts: List[str], as_of_T: datetime) -> Set[str]:
        """
        Find ATMs historically used for cashouts by any account in the mule chain prior to time T.
        Used for Stage 0 Network-linked ATM candidate retrieval.
        """
        if self.withdrawals_df.empty or not chain_accounts:
            return set()

        acc_set = set(str(a).strip() for a in chain_accounts)
        prior_wds = self.withdrawals_df[
            (self.withdrawals_df["account_id"].isin(acc_set)) &
            (self.withdrawals_df["ts"] < as_of_T)
        ]
        return set(prior_wds["atm_id"].dropna().unique())
