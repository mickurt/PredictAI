import os
import json
import logging
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    logger.warning("Supabase config not found in .env!")
    supabase = None

def init_db():
    if not supabase: return
    try:
        # Check if portfolio_history has data
        res = supabase.table("portfolio_history").select("id").limit(1).execute()
        if not res.data:
            # Initialize with starting balance
            supabase.table("portfolio_history").insert({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_value": 100.0
            }).execute()
            
            supabase.table("transactions").insert({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "category": 'DEPOSIT',
                "amount": 100.0,
                "asset": 'USD',
                "detail": 'Initial Deposit',
                "price": None,
                "gain": 0.0
            }).execute()
    except Exception as e:
        logger.error(f"DB Init Error: {e}")

def log_portfolio_value(value):
    if not supabase: return
    try:
        supabase.table("portfolio_history").insert({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_value": value
        }).execute()
    except Exception as e:
        logger.error(f"log_portfolio_value error: {e}")

def log_transaction(category, amount, asset, detail, price=0.0, gain=0.0):
    if not supabase: return
    try:
        supabase.table("transactions").insert({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "amount": amount,
            "asset": asset,
            "detail": detail,
            "price": price,
            "gain": gain
        }).execute()
    except Exception as e:
        logger.error(f"log_transaction error: {e}")

def get_portfolio_history():
    if not supabase: return []
    try:
        res = supabase.table("portfolio_history").select("timestamp, total_value").order("timestamp").execute()
        return [(r['timestamp'], r['total_value']) for r in res.data]
    except Exception as e:
        return []

def get_transactions():
    if not supabase: return []
    try:
        res = supabase.table("transactions").select("*").order("timestamp", desc=True).limit(50).execute()
        return [(r['id'], r['timestamp'], r['category'], r['amount'], r['asset'], r['detail'], r['price'], r['gain']) for r in res.data]
    except Exception as e:
        return []

def get_total_deposited():
    if not supabase: return 0.0
    try:
        res = supabase.table("transactions").select("amount").eq("category", "DEPOSIT").execute()
        return float(sum(r['amount'] or 0.0 for r in res.data))
    except Exception as e:
        return 0.0

def reconstruct_portfolio_state():
    if not supabase: return 0.0, {}
    try:
        res = supabase.table("transactions").select("category, amount, asset, price").order("timestamp").execute()
        txs = [(r['category'], r['amount'], r['asset'], r['price']) for r in res.data]
        
        balance = 0.0
        portfolio = {}

        for category, amount, asset, price in txs:
            amt = float(amount or 0)
            px = float(price or 1.0)
            if px <= 0: px = 1.0

            if category == "DEPOSIT":
                balance += amt
            elif category == "BUY":
                balance -= amt
                shares_bought = amt / px
                if asset not in portfolio:
                    portfolio[asset] = {'shares': 0.0, 'avg_price': 0.0}
                
                curr_shares = portfolio[asset]['shares']
                curr_avg = portfolio[asset]['avg_price']
                total_shares = curr_shares + shares_bought
                
                new_avg = ((curr_shares * curr_avg) + (shares_bought * px)) / total_shares if total_shares > 0 else px
                portfolio[asset]['shares'] = total_shares
                portfolio[asset]['avg_price'] = new_avg
                
            elif category == "SELL":
                balance += amt
                shares_sold = amt / px
                if asset in portfolio:
                    portfolio[asset]['shares'] = max(0.0, portfolio[asset]['shares'] - shares_sold)
                    if portfolio[asset]['shares'] < 0.000001:
                        del portfolio[asset]
                        
        return balance, portfolio
    except Exception as e:
        logger.error(f"reconstruct_portfolio_state error: {e}")
        return 0.0, {}

def reset_db():
    if not supabase: return
    try:
        # Supabase doesn't allow unqualified bulk deletes with REST easily, 
        # but we can filter by id > 0 since it's identity.
        supabase.table("transactions").delete().gt("id", -1).execute()
        supabase.table("portfolio_history").delete().gt("id", -1).execute()
        init_db()
    except Exception as e:
        logger.error(f"reset_db error: {e}")


if __name__ == "__main__":
    init_db()
