import sqlite3
import datetime

DB_NAME = "database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Create transactions table
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  category TEXT,
                  amount REAL,
                  asset TEXT,
                  detail TEXT,
                  price REAL,
                  gain REAL)''')
    
    # Simple migration for existing tables: try adding columns if they fail
    try:
        c.execute("ALTER TABLE transactions ADD COLUMN price REAL")
    except sqlite3.OperationalError:
        pass # Column likely exists
        
    try:
        c.execute("ALTER TABLE transactions ADD COLUMN gain REAL")
    except sqlite3.OperationalError:
        pass

    # Create portfolio history table
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  total_value REAL)''')
    
    # Initialize with starting balance if empty
    c.execute("SELECT count(*) FROM portfolio_history")
    count = c.fetchone()[0]
    if count == 0:
        c.execute("INSERT INTO portfolio_history (timestamp, total_value) VALUES (?, ?)",
                  (datetime.datetime.now().isoformat(), 100.0))
        # Initial deposit price is NULL (None) so it shows empty in UI
        c.execute("INSERT INTO transactions (timestamp, category, amount, asset, detail, price, gain) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (datetime.datetime.now().isoformat(), 'DEPOSIT', 100.0, 'USD', 'Initial Deposit', None, 0.0))
    
    conn.commit()
    conn.close()

def log_portfolio_value(value):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO portfolio_history (timestamp, total_value) VALUES (?, ?)",
              (datetime.datetime.now().isoformat(), value))
    conn.commit()
    conn.close()

def log_transaction(category, amount, asset, detail, price=0.0, gain=0.0):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO transactions (timestamp, category, amount, asset, detail, price, gain) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (datetime.datetime.now().isoformat(), category, amount, asset, detail, price, gain))
    conn.commit()
    conn.close()

def get_portfolio_history():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT timestamp, total_value FROM portfolio_history ORDER BY timestamp ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_transactions():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, timestamp, category, amount, asset, detail, price, gain FROM transactions ORDER BY timestamp DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return rows

def get_total_deposited():
    """Calculates the sum of all DEPOSIT transactions."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM transactions WHERE category='DEPOSIT'")
    result = c.fetchone()[0]
    conn.close()
    return float(result or 0.0)

def reconstruct_portfolio_state():
    """
    Replays transactions to rebuild:
    - Current Cash Balance
    - Portfolio State: { 'ASSET': {'shares': 10.5, 'avg_price': 0.65} }
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT category, amount, asset, price FROM transactions ORDER BY timestamp ASC")
    txs = c.fetchall()
    conn.close()

    balance = 0.0
    # Portfolio stores: {'shares': float, 'avg_price': float}
    portfolio = {}

    for category, amount, asset, price in txs:
        amt = float(amount or 0)
        px = float(price or 1.0) # Default to 1.0 for legacy
        if px <= 0: px = 1.0     # Avoid div by zero

        if category == "DEPOSIT":
            balance += amt
        elif category == "BUY":
            balance -= amt
            shares_bought = amt / px
            
            if asset not in portfolio:
                portfolio[asset] = {'shares': 0.0, 'avg_price': 0.0}
            
            # Weighted Average Price update
            current_shares = portfolio[asset]['shares']
            current_avg = portfolio[asset]['avg_price']
            
            total_shares = current_shares + shares_bought
            new_avg = ((current_shares * current_avg) + (shares_bought * px)) / total_shares if total_shares > 0 else px
            
            portfolio[asset]['shares'] = total_shares
            portfolio[asset]['avg_price'] = new_avg
            
        elif category == "SELL":
            balance += amt
            # Reduce shares, avg_price stays same (FIFO/Average Cost assumption)
            shares_sold = amt / px
            if asset in portfolio:
                portfolio[asset]['shares'] = max(0.0, portfolio[asset]['shares'] - shares_sold)
                if portfolio[asset]['shares'] < 0.000001: # Float epsilon
                    del portfolio[asset]
        
    return balance, portfolio

def reset_db():
    """Drops all tables and re-initializes the database."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS transactions")
    c.execute("DROP TABLE IF EXISTS portfolio_history")
    conn.commit()
    conn.close()
    init_db()

if __name__ == "__main__":
    init_db()
