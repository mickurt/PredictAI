from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import schedule
import time
import threading
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from db import init_db, log_portfolio_value, log_transaction, get_transactions, get_portfolio_history, reconstruct_portfolio_state, reset_db, get_total_deposited
from logic import DecisionEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InvestmentBot")

app = FastAPI(title="Gemini Investment Dashboard")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state (simulated current balance)
current_balance = 100.0  # Default, overwritten by DB
portfolio = {}  # Default, overwritten by DB
trading_preferences = {
    "stocks": True,
    "crypto": True, 
    "polymarket": True
}

# Initialize DB on startup
@app.on_event("startup")
def setup():
    init_db()
    
    # Load state from database to persist across restarts
    global current_balance, portfolio
    c_bal, port = reconstruct_portfolio_state()
    # If DB was just initialized with 100 DEPOSIT, reconstruct_portfolio_state returns 100.
    # If DB was empty (fresh install), init_db adds 100 DEPOSIT, then reconstruct returns 100.
    # So we can safely trust reconstruct_portfolio_state.
    current_balance = c_bal
    portfolio = port
    
    logger.info(f"System State Loaded: Balance=${current_balance}, Portfolio={portfolio}")

    # Log current state immediately so chart is up to date
    # Fix: portfolio values are dicts now
    total_holdings = sum(v['shares'] * v['avg_price'] for v in portfolio.values())
    total_val = current_balance + total_holdings
    log_portfolio_value(total_val)

    # Start the scheduler in a background thread
    threading.Thread(target=run_scheduler, daemon=True).start()

def run_scheduler():
    """Runs the investment logic every 5 minutes."""
    while True:
        schedule.run_pending()
        time.sleep(1)

def investment_job():
    global current_balance, portfolio, trading_preferences
    logger.info("Running scheduled investment analysis...")
    
    # Estimate current portfolio value dict for Gemini
    # portfolio structure: {'ASSET': {'shares': 10, 'avg_price': 0.5}}
    total_invested = sum(v['shares'] * v['avg_price'] for v in portfolio.values())
    total_portfolio_value = current_balance + total_invested
    
    engine = DecisionEngine()
    decision = engine.get_market_analysis(current_balance, portfolio, trading_preferences)
    
    action = decision.get("action")
    asset = decision.get("asset")
    amount = float(decision.get("amount") or 0)
    price = float(decision.get("price") or 1.0)
    reasoning = decision.get("reasoning")
    
    gain = 0.0

    if action == "BUY":
        # DIVERSIFICATION GUARDRAIL: Max 40% in one asset
        current_asset_val = 0.0
        if asset in portfolio:
            current_asset_val = portfolio[asset]['shares'] * portfolio[asset]['avg_price']
            
        max_position_size = total_portfolio_value * 0.40
        proposed_total = current_asset_val + amount
        
        if proposed_total > max_position_size:
            allowed_buy = max_position_size - current_asset_val
            if allowed_buy < 2.0: # If less than $2 room left, just block it
                logger.warning(f"Blocked BUY {asset}: Position limit reached ({current_asset_val:.2f} / {max_position_size:.2f})")
                log_transaction("WATCH", 0, asset, "Diversification limit reached (Max 40%)", price, 0.0)
                return # Skip this turn
            else:
                logger.info(f"Capping BUY {asset} from ${amount} to ${allowed_buy:.2f} (Diversification Rule)")
                amount = allowed_buy

        if current_balance >= amount and amount > 0:
            current_balance -= amount
            shares_bought = amount / price
            
            if asset not in portfolio:
                portfolio[asset] = {'shares': 0.0, 'avg_price': 0.0}
            
            # Weighted Avg Price
            curr_shares = portfolio[asset]['shares']
            curr_avg = portfolio[asset]['avg_price']
            total_shares = curr_shares + shares_bought
            
            new_avg = ((curr_shares * curr_avg) + (shares_bought * price)) / total_shares if total_shares > 0 else price
            
            portfolio[asset]['shares'] = total_shares
            portfolio[asset]['avg_price'] = new_avg
            
            log_transaction("BUY", amount, asset, reasoning, price, 0.0)
            logger.info(f"Executed BUY {asset}: ${amount:.2f} @ ${price}")
        else:
             logger.warning(f"Insufficient funds to BUY {asset}: ${amount} (Balance: ${current_balance})")
            
    elif action == "SELL":
        if asset in portfolio:
            # Check if we have enough value. 'amount' from Gemini is usually USD target to sell.
            # Convert USD amount to shares
            # We use the CURRENT execution price to determine how many shares to sell
            shares_to_sell = amount / price
            
            if portfolio[asset]['shares'] >= shares_to_sell:
                # Calculate Realized Gain/Loss %
                # (Sell Price - Avg Buy Price) / Avg Buy Price
                avg_buy_price = portfolio[asset]['avg_price']
                if avg_buy_price > 0:
                    gain_pct = ((price - avg_buy_price) / avg_buy_price) * 100
                else:
                    gain_pct = 0.0
                
                current_balance += amount
                portfolio[asset]['shares'] -= shares_to_sell
                
                # Cleanup if empty
                if portfolio[asset]['shares'] < 0.000001:
                    del portfolio[asset]
                    
                log_transaction("SELL", amount, asset, reasoning, price, gain_pct)
                logger.info(f"Executed SELL {asset}: ${amount} @ ${price} (Gain: {gain_pct:.2f}%)")
            else:
                 logger.warning(f"Insufficient shares to SELL {asset}. Request: {shares_to_sell}, Held: {portfolio[asset]['shares']}")

    elif action == "HOLD":
        if asset in portfolio and portfolio[asset]['shares'] > 0:
            log_transaction("HOLD", 0, asset, reasoning, price, 0.0)
            logger.info(f"Holding position on {asset}. Reasoning: {reasoning}")
        else:
            log_transaction("WATCH", 0, asset, reasoning, price, 0.0)
            logger.info(f"Watching {asset} (No position). Reasoning: {reasoning}")
    
    elif action == "WATCH":
        log_transaction("WATCH", 0, asset, reasoning, price, 0.0)
        logger.info(f"Watching {asset}. Reasoning: {reasoning}")

    # Calculate Total Portfolio Value using LATEST prices
    # For assets not traded this turn, we ideally update their price.
    # For now, we use the price from the transaction if available, or keep old estimate.
    
    # Simple Valuation: Cost Basis
    total_holdings_val = sum(v['shares'] * v['avg_price'] for v in portfolio.values())
    
    # Simulate market fluctuation on the HOLDINGS only
    # Cash (current_balance) does not fluctuate.
    if total_holdings_val > 0:
        import random
        fluctuation = random.uniform(0.99, 1.01)
        fluctuated_holdings = total_holdings_val * fluctuation
    else:
        fluctuated_holdings = 0.0

    log_value = current_balance + fluctuated_holdings
    
    log_portfolio_value(log_value)
    logger.info(f"Estimated Portfolio Value: ${log_value:.2f}")

# Schedule the job every 5 minutes
schedule.every(5).minutes.do(investment_job)

@app.get("/api/settings")
def get_settings():
    return trading_preferences

@app.post("/api/settings")
def update_settings(prefs: dict):
    global trading_preferences
    trading_preferences.update(prefs)
    return {"status": "updated", "settings": trading_preferences}

@app.get("/api/status")
def get_status():
    """Returns current system status and balance."""
    # Calculate holdings value from new structure
    total_holdings = sum(v['shares'] * v['avg_price'] for v in portfolio.values())
    total_value = current_balance + total_holdings
    
    # Calculate Net Performance (excluding deposits)
    total_invested = get_total_deposited()
    # Avoid division by zero
    performance_pct = ((total_value - total_invested) / total_invested * 100) if total_invested > 0 else 0.0
    
    # Flatten portfolio for frontend (Asset -> Value)
    flat_portfolio = {k: v['shares'] * v['avg_price'] for k, v in portfolio.items()}
    
    return {
        "balance": current_balance,
        "holdings": total_holdings,
        "total_value": total_value,
        "total_invested": total_invested,
        "performance_pct": performance_pct,
        "portfolio": flat_portfolio
    }

@app.get("/api/history")
def get_history():
    """Returns historical portfolio value for charts."""
    return get_portfolio_history()

@app.get("/api/transactions")
def list_transactions():
    """Returns distinct actions taken by the bot."""
    return get_transactions()

@app.post("/api/run")
def run_analysis():
    """Trigger the investment analysis manually."""
    thread = threading.Thread(target=investment_job)
    thread.start()
    return {"status": "Analysis started"}

@app.post("/api/reset")
def reset_system():
    """Wipe database and reset to initial state."""
    global current_balance, portfolio
    reset_db()
    
    # Re-initialize state (should be 100 on Deposit)
    c_bal, port = reconstruct_portfolio_state()
    current_balance = c_bal
    portfolio = port
    
    log_portfolio_value(current_balance) # Log initial state
    logger.info("SYSTEM RESET: Database wiped and restarted.")
    
    return {"status": "Reset complete", "balance": current_balance}

@app.post("/api/deposit")
def deposit_funds():
    global current_balance
    amount = 1000.0
    current_balance += amount
    log_transaction("DEPOSIT", amount, "USD", "Test Deposit", 1.0, 0.0)
    logger.info(f"Deposited ${amount}. New Balance: ${current_balance}")
    return {"status": "success", "new_balance": current_balance}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
