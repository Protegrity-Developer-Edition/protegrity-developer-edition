"""Banking data service – loads customer data and provides query methods."""
from __future__ import annotations
import json, hashlib, logging
from pathlib import Path
from typing import Optional

from services.protegrity_guard import _strip_pii_tags

log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "banking_data"
CUSTOMERS_FILE = DATA_DIR / "customers_protected.json"
CREDENTIALS_FILE = DATA_DIR / "credentials.json"

# Lazy-loaded guard reference for unprotecting tokenized fields
_guard = None


def _get_guard():
    """Lazy-load the Protegrity guard to avoid circular imports."""
    global _guard
    if _guard is None:
        try:
            from services.protegrity_guard import get_guard
            _guard = get_guard()
        except Exception as e:
            log.warning("Could not load protegrity_guard: %s", e)
    return _guard


def _unprotect(text: str) -> str:
    """Unprotect tokenized text using the SDK. Falls back to stripping tags."""
    guard = _get_guard()
    if guard is not None:
        try:
            result = guard.find_and_unprotect(text)
            return result.transformed_text
        except Exception as e:
            log.warning("find_and_unprotect failed: %s — stripping tags", e)
    return _strip_pii_tags(text)


class BankingService:
    def __init__(self):
        self.customers: dict[str, dict] = {}
        self.credentials: list[dict] = []
        self._load_data()

    def _load_data(self):
        if CUSTOMERS_FILE.exists():
            with open(CUSTOMERS_FILE) as f:
                customers_list = json.load(f)
            for c in customers_list:
                self.customers[c["customer_id"]] = c
            log.info("Loaded %d customers from %s", len(self.customers), CUSTOMERS_FILE.name)
        else:
            # Fallback to unprotected file
            fallback = DATA_DIR / "customers.json"
            if fallback.exists():
                with open(fallback) as f:
                    customers_list = json.load(f)
                for c in customers_list:
                    self.customers[c["customer_id"]] = c
                log.warning("customers_protected.json not found — loaded %d from customers.json", len(self.customers))

        if CREDENTIALS_FILE.exists():
            with open(CREDENTIALS_FILE) as f:
                self.credentials = json.load(f)
            log.info("Loaded %d credentials", len(self.credentials))

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        for cred in self.credentials:
            if cred["username"] == username and cred["password_hash"] == pw_hash:
                customer_id = cred["customer_id"]
                # Get name from protected data and unprotect via SDK
                customer = self.customers.get(customer_id)
                if customer:
                    raw_name = customer.get("name", "")
                    display_name = _unprotect(raw_name) if "[" in raw_name else raw_name
                else:
                    display_name = "Customer"
                return {"customer_id": customer_id, "name": display_name}
        return None

    def get_all_customers(self) -> list[dict]:
        """Return list of all customers."""
        return list(self.customers.values())

    def get_customer(self, customer_id: str) -> dict | None:
        """Return full customer record by ID."""
        return self.customers.get(customer_id)

    def get_account_summary(self, customer_id: str) -> Optional[dict]:
        c = self.customers.get(customer_id)
        if not c:
            return None

        # Unprotect the customer name
        raw_name = c.get("name", "")
        display_name = _unprotect(raw_name) if "[" in raw_name else raw_name

        accounts = []
        for a in c.get("accounts", []):
            acct_num = a.get("account_number", "")
            # Unprotect then mask — get real last 4 digits
            clear_num = _unprotect(acct_num) if "[" in acct_num else acct_num
            accounts.append({
                "account_id": a["account_id"],
                "account_number_masked": "****" + clear_num[-4:],
                "type": a["type"],
                "balance": a["balance"],
                "currency": a.get("currency", "USD"),
                "status": a["status"],
            })

        cards = []
        for cc in c.get("credit_cards", []):
            card_num = cc.get("card_number", "")
            clear_card = _unprotect(card_num) if "[" in card_num else card_num
            cards.append({
                "card_id": cc["card_id"],
                "last_four": clear_card[-4:],
                "card_type": cc["card_type"],
                "card_tier": cc["card_tier"],
                "credit_limit": cc["credit_limit"],
                "current_balance": cc["current_balance"],
                "available_credit": cc["available_credit"],
                "reward_points": cc["reward_points"],
                "status": cc["status"],
                "expiration": cc["expiration"],
            })

        txns = sorted(c.get("transactions", []), key=lambda t: t["date"], reverse=True)

        return {
            "customer_id": customer_id,
            "name": display_name,
            "accounts": accounts,
            "credit_cards": cards,
            "contracts": c.get("contracts", []),
            "recent_transactions": txns[:20],
        }


_service_instance = None


def get_banking_service() -> BankingService:
    global _service_instance
    if _service_instance is None:
        _service_instance = BankingService()
    return _service_instance