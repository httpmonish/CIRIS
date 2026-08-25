"""
Money-Flow Graph Engine for CIRIS.

Extracts point-in-time temporal subgraphs, traces multi-hop fund propagation,
identifies branching/fragmentation paths, and measures mule cluster centralities.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict, deque


class MoneyFlowGraphEngine:
    """
    Generalized financial relationship graph engine for multi-hop money flow tracing.
    """

    def __init__(
        self,
        graph_edges_df: Optional[pd.DataFrame] = None,
        case_links_df: Optional[pd.DataFrame] = None,
        withdrawals_df: Optional[pd.DataFrame] = None,
        upi_df: Optional[pd.DataFrame] = None,
    ):
        self.edges_df = graph_edges_df.copy() if graph_edges_df is not None else pd.DataFrame()
        self.case_links_df = case_links_df.copy() if case_links_df is not None else pd.DataFrame()
        self.withdrawals_df = withdrawals_df.copy() if withdrawals_df is not None else pd.DataFrame()
        self.upi_df = upi_df.copy() if upi_df is not None else pd.DataFrame()

        self._preprocess_data()

    def _preprocess_data(self) -> None:
        """Standardize column names and parse timestamps."""
        if not self.edges_df.empty:
            col_map = {
                "source": "source_account",
                "target": "destination_account",
                "src": "source_account",
                "dst": "destination_account",
                "from_account": "source_account",
                "to_account": "destination_account",
                "time": "timestamp",
                "txn_timestamp": "timestamp",
            }
            self.edges_df.rename(columns=col_map, inplace=True)
            if "timestamp" in self.edges_df.columns:
                self.edges_df["timestamp"] = pd.to_datetime(self.edges_df["timestamp"], errors="coerce")
            if "amount" not in self.edges_df.columns:
                self.edges_df["amount"] = 1000.0

        if not self.withdrawals_df.empty:
            if "timestamp" in self.withdrawals_df.columns:
                self.withdrawals_df["timestamp"] = pd.to_datetime(self.withdrawals_df["timestamp"], errors="coerce")

    def extract_point_in_time_subgraph(
        self,
        seed_accounts: List[str],
        as_of_T: datetime,
        max_hops: int = 3,
    ) -> Dict[str, Any]:
        """
        Extract directed money-flow subgraph strictly bounded by timestamp T.
        """
        if self.edges_df.empty or not seed_accounts:
            return {
                "nodes": seed_accounts,
                "edges": [],
                "hop_map": {acc: 0 for acc in seed_accounts},
                "cluster_size": len(seed_accounts),
            }

        # Temporal filter: t <= T
        if "timestamp" in self.edges_df.columns:
            valid_edges = self.edges_df[self.edges_df["timestamp"] <= as_of_T].copy()
        else:
            valid_edges = self.edges_df.copy()

        if valid_edges.empty:
            return {
                "nodes": seed_accounts,
                "edges": [],
                "hop_map": {acc: 0 for acc in seed_accounts},
                "cluster_size": len(seed_accounts),
            }

        # BFS for k-hop forward and backward neighborhood
        adj_out = defaultdict(list)
        adj_in = defaultdict(list)
        edge_records = []

        for idx, row in valid_edges.iterrows():
            src = str(row["source_account"])
            dst = str(row["destination_account"])
            amt = float(row.get("amount", 1000.0))
            ts = row.get("timestamp", as_of_T)

            adj_out[src].append((dst, amt, ts))
            adj_in[dst].append((src, amt, ts))
            edge_records.append({"source": src, "target": dst, "amount": amt, "timestamp": ts})

        visited_nodes: Set[str] = set(seed_accounts)
        hop_map: Dict[str, int] = {acc: 0 for acc in seed_accounts}
        queue = deque([(acc, 0) for acc in seed_accounts])

        collected_edges = []

        while queue:
            curr_node, depth = queue.popleft()
            if depth >= max_hops:
                continue

            for nxt, amt, ts in adj_out.get(curr_node, []):
                collected_edges.append({
                    "source": curr_node,
                    "target": nxt,
                    "amount": amt,
                    "timestamp": ts,
                    "direction": "FORWARD",
                })
                if nxt not in visited_nodes:
                    visited_nodes.add(nxt)
                    hop_map[nxt] = depth + 1
                    queue.append((nxt, depth + 1))

            for prev, amt, ts in adj_in.get(curr_node, []):
                collected_edges.append({
                    "source": prev,
                    "target": curr_node,
                    "amount": amt,
                    "timestamp": ts,
                    "direction": "BACKWARD",
                })
                if prev not in visited_nodes:
                    visited_nodes.add(prev)
                    hop_map[prev] = depth + 1
                    queue.append((prev, depth + 1))

        return {
            "nodes": sorted(list(visited_nodes)),
            "edges": collected_edges,
            "hop_map": hop_map,
            "cluster_size": len(visited_nodes),
        }

    def find_money_paths(
        self,
        source_account: str,
        as_of_T: datetime,
        max_hops: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Discover directed money-flow paths from a source account.
        """
        subgraph = self.extract_point_in_time_subgraph([source_account], as_of_T=as_of_T, max_hops=max_hops)
        edges = subgraph["edges"]

        if not edges:
            return [{
                "path_id": f"PATH_{source_account}_DIRECT",
                "nodes": [source_account],
                "total_amount_flow": 0.0,
                "hop_count": 0,
                "endpoint_type": "TRANSFER",
            }]

        # Construct simple paths
        paths = []
        adj = defaultdict(list)
        for e in edges:
            if e["direction"] == "FORWARD":
                adj[e["source"]].append((e["target"], e["amount"]))

        def dfs(curr: str, current_path: List[str], current_amt: float, depth: int):
            if depth >= max_hops or curr not in adj or not adj[curr]:
                if len(current_path) > 1:
                    paths.append({
                        "path_id": f"PATH_{source_account}_{len(paths)+1}",
                        "nodes": list(current_path),
                        "total_amount_flow": current_amt,
                        "hop_count": len(current_path) - 1,
                        "endpoint_type": "ATM" if depth == 1 else ("MERCHANT" if depth == 2 else "TRANSFER"),
                    })
                return

            for nxt, amt in adj[curr]:
                if nxt not in current_path:  # avoid cycles
                    dfs(nxt, current_path + [nxt], min(current_amt, amt) if current_amt > 0 else amt, depth + 1)

        dfs(source_account, [source_account], 0.0, 0)

        if not paths:
            paths.append({
                "path_id": f"PATH_{source_account}_DEFAULT",
                "nodes": [source_account],
                "total_amount_flow": 0.0,
                "hop_count": 0,
                "endpoint_type": "TRANSFER",
            })

        return paths
