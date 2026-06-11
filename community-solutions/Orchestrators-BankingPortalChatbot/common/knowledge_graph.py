"""
Shared Knowledge Graph built from customers_protected.json.

Nodes: Customer, Account, CreditCard, Loan
Edges: HAS_ACCOUNT, HAS_CARD, HAS_LOAN

All PII fields stored as Protegrity tokens — the graph never contains real PII.
"""

from __future__ import annotations

import json
import os
from typing import Optional, List, Dict, Any

import networkx as nx

_GRAPH: Optional[nx.DiGraph] = None

DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "banking_data", "customers_protected.json",
)
GRAPH_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "banking_data", "knowledge_graph.json",
)


def _build_graph() -> nx.DiGraph:
    """Build knowledge graph from protected customer data."""
    G = nx.DiGraph()

    with open(DATA_FILE, "r") as f:
        customers = json.load(f)

    for cust in customers:
        cid = cust["customer_id"]
        G.add_node(cid, node_type="Customer", **{
            k: cust.get(k, "") for k in
            ["name", "email", "phone", "ssn", "address", "dob"]
        })

        # Accounts (field is "accounts" in the JSON, not "bank_accounts")
        for acct in cust.get("accounts", []):
            aid = acct.get("account_id", "")
            if not aid:
                continue
            safe = {k: v for k, v in acct.items() if k != "account_id"}
            safe["acct_type"] = safe.pop("type", "")
            G.add_node(aid, node_type="Account", **safe)
            G.add_edge(cid, aid, relation="HAS_ACCOUNT")

        # Credit cards
        for card in cust.get("credit_cards", []):
            card_id = card.get("card_id", "")
            if not card_id:
                continue
            safe = {k: v for k, v in card.items() if k != "card_id"}
            G.add_node(card_id, node_type="CreditCard", **safe)
            G.add_edge(cid, card_id, relation="HAS_CARD")

        # Contracts/Loans (field is "contracts" in the JSON, not "loans")
        for contract in cust.get("contracts", []):
            contract_id = contract.get("contract_id", "")
            if not contract_id:
                continue
            safe = {k: v for k, v in contract.items() if k != "contract_id"}
            safe["loan_type"] = safe.pop("type", "")
            G.add_node(contract_id, node_type="Loan", **safe)
            G.add_edge(cid, contract_id, relation="HAS_LOAN")

        # Transactions — link to both customer and account
        for txn in cust.get("transactions", []):
            txn_id = txn.get("transaction_id", "")
            if not txn_id:
                continue
            # Store only summary fields to keep graph lean
            G.add_node(txn_id, node_type="Transaction",
                       date=txn.get("date", ""),
                       amount=txn.get("amount", 0),
                       category=txn.get("category", ""),
                       merchant=txn.get("merchant", ""),
                       txn_type=txn.get("type", ""),
                       status=txn.get("status", ""),
                       account_id=txn.get("account_id", ""))
            G.add_edge(cid, txn_id, relation="HAS_TRANSACTION")
            # Link transaction to account if it exists
            acct_id = txn.get("account_id", "")
            if acct_id and acct_id in G:
                G.add_edge(acct_id, txn_id, relation="ACCOUNT_TRANSACTION")

    return G


def get_graph() -> nx.DiGraph:
    """Return cached graph, building if needed."""
    global _GRAPH
    if _GRAPH is None:
        if os.path.exists(GRAPH_FILE):
            _GRAPH = nx.node_link_graph(
                json.load(open(GRAPH_FILE, "r")),
            )
        else:
            _GRAPH = _build_graph()
    return _GRAPH


def save_graph() -> None:
    """Persist graph to JSON."""
    G = get_graph()
    with open(GRAPH_FILE, "w") as f:
        json.dump(nx.node_link_data(G), f, indent=2, default=str)


def query_customer(customer_id: str) -> Dict[str, Any]:
    """Return customer node + all connected entities."""
    G = get_graph()
    if customer_id not in G:
        return {}

    data = dict(G.nodes[customer_id])
    data["customer_id"] = customer_id

    neighbors = {}
    for _, target, edge_data in G.out_edges(customer_id, data=True):
        relation = edge_data.get("relation", "RELATED")
        neighbors.setdefault(relation, []).append(
            {"id": target, **dict(G.nodes[target])}
        )
    data["relations"] = neighbors
    return data


def search_nodes(query: str, node_type: Optional[str] = None) -> List[Dict]:
    """Search graph nodes by substring match on any attribute."""
    G = get_graph()
    results = []
    q = query.lower()
    for node, attrs in G.nodes(data=True):
        if node_type and attrs.get("node_type") != node_type:
            continue
        searchable = " ".join(str(v) for v in attrs.values()).lower()
        if q in searchable or q in node.lower():
            results.append({"id": node, **attrs})
    return results
