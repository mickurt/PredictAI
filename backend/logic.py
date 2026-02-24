import os
import random
import json
import logging
from datetime import datetime, timedelta, timezone
import yfinance as yf

# Try to import google-generativeai, handle if missing
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

logger = logging.getLogger(__name__)

class DecisionEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.valid_models = []
        
        if self.api_key and HAS_GENAI:
            genai.configure(api_key=self.api_key)
            
            # Priorities as requested: 2.5-lite -> 2.5-flash -> 2.5-pro -> 3-flash -> 3-pro
            preferred_order = [
                'gemini-2.5-flash-lite',
                'gemini-2.5-flash',
                'gemini-2.5-pro',
                'gemini-3-flash-preview',
                'gemini-3-pro-preview', 
                'gemini-2.0-flash-lite',
                'gemini-2.0-flash',
                'gemini-1.5-flash'
            ]
            
            self.valid_models = self._init_valid_models(preferred_order)
            logger.info(f"Initialized DecisionEngine with fallback chain: {self.valid_models}")
        else:
            logger.warning("Generative AI not available.")

    def _init_valid_models(self, preferred):
        """Filter preferred models against what is actually available via API"""
        try:
            # Get list of available models from API
            available_models = [m.name for m in genai.list_models()]
            # logger.info(f"Available Gemini Models: {available_models}") 
            
            valid = []
            for p in preferred:
                # Check if the preferred model name is contained in any available model string
                if any(p in m for m in available_models):
                    valid.append(p)
            
            if not valid:
                logger.warning("No preferred models found! Defaulting to basic fallback.")
                return ['gemini-1.5-flash']
                
            return valid
        except Exception as e:
            logger.error(f"Failed to list models: {e}. Using default list.")
            return preferred

    def _is_market_open(self):
        """Check if US Market is open (Mon-Fri 14:30-21:00 UTC)."""
        now = datetime.now(timezone.utc)
        if now.weekday() >= 5: return False # Weekend
        # Simple UTC check for 9:30 ET - 16:00 ET (Roughly 13:30/14:30 to 20:00/21:00 UTC)
        minutes = now.hour * 60 + now.minute
        return 810 <= minutes <= 1260

    def get_market_analysis(self, current_balance, portfolio, preferences=None):
        """
        Generates an investment decision (BUY/SELL/HOLD) based on market data.
        """
        # Handle Preferences
        if preferences is None:
            preferences = {"stocks": True, "crypto": True, "polymarket": True}

        disabled_assets = [k.capitalize() for k, v in preferences.items() if not v]
        restriction_note = ""
        if disabled_assets:
            restriction_note = f"IMPORTANT RESTRICTION: The user has DISABLED buying: {', '.join(disabled_assets)}. You CANNOT BUY these types. You may HOLD or SELL existing positions."

        # Randomly vary market sentiment
        sentiment = random.choice(["Bullish", "Bearish", "Volatile", "Neutral"])
        
        today_date = datetime.now().strftime("%Y-%m-%d")
        market_open = self._is_market_open()
        
        # Format Market Data
        
        real_markets = [] 
        market_context_str = f"Today's Date: {today_date}\n"
        
        # 1. POLYMARKET
        if preferences.get("polymarket", True):
            from polymarket import get_top_markets
            real_markets = get_top_markets(limit=20)
            
            market_context_str += "\nREAL-TIME POLYMARKET PRICES (Title | Prices | Deadline | Slug):\n"
            today_date_obj = datetime.now().date()
            for m in real_markets:
                 deadline = m.get('deadline', 'Unknown')
                 
                 days_left_str = ""
                 try:
                     if deadline != 'Unknown':
                         d_str = deadline.split('T')[0]
                         target_date = datetime.strptime(d_str, "%Y-%m-%d").date()
                         days = (target_date - today_date_obj).days
                         
                         if days < 0:
                             days_left_str = "(Expired)"
                         elif days == 0:
                             days_left_str = "(Expiring Today)"
                         else:
                             days_left_str = f"({days} days left)"
                 except:
                     pass

                 market_context_str += f"- {m['title']} | {m['prices']} | Ends: {deadline} {days_left_str} | POLY:{m['slug']}\n"
        else:
            market_context_str += "Polymarket Trading: DISABLED (Do not buy Polymarket assets).\n"

        # 2. CRYPTO
        if preferences.get("crypto", True):
            try:
                cryptos = ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "XRP-USD"]
                market_context_str += "\nREAL-TIME CRYPTO PRICES (Ticker | Price | 24h Change):\n"
                # Fetch data
                tickers = yf.Tickers(" ".join(cryptos))
                for symbol in cryptos:
                    try:
                        info = tickers.tickers[symbol].fast_info
                        price = info.last_price
                        prev_close = info.previous_close
                        change_percent = ((price - prev_close) / prev_close) * 100 if prev_close else 0.0
                        market_context_str += f"- {symbol} | ${price:.2f} | 24h Change: {change_percent:+.2f}% | Ticker: {symbol}\n"
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error fetching crypto: {e}")
        else:
             market_context_str += "Crypto Trading: DISABLED.\n"

        # 3. STOCKS (Real Market Hours Only)
        if preferences.get("stocks", True):
            if market_open:
                try:
                    # Expanded Universe (Top Tech + Crypto Proxies + High Volatility + Big Caps + Key Sectors)
                    stock_universe = [
                        "NVDA", "TSLA", "MSTR", "COIN", "PLTR", "AMD", "META", "GOOGL", "AMZN", "MSFT", "AAPL", 
                        "NFLX", "INTC", "SMCI", "ARM", "HOOD", "MARA", "RIOT", "CLSK", "CVNA", "UPST", "AFRM",
                        "SOFI", "PYPL", "SQ", "SHOP", "UBER", "ABNB", "CRWD", "PANW", "SNOW", "DDOG", "NET",
                        "DKNG", "RBLX", "U", "TTD", "ZS", "MDB", "TEAM", "WDAY", "ADBE", "CRM", "ORCL",
                        "IBM", "QCOM", "TXN", "AVGO", "CSCO", "GME", "AMC", "DJT",
                        
                        # --- ADDITIONS: BIG CAPS & KEY SECTORS ---
                        
                        # Semiconductors & Equipment
                        "ASML", "LRCX", "MU", "AMAT", "ADI", "KLAC",
                        
                        # Finance & Fintech
                        "JPM", "GS", "MS", "BAC", "V", "MA", "AXP", "BLK",
                        
                        # Healthcare & Biotech
                        "LLY", "NVO", "UNH", "PFE", "ABBV", "MRK", "AMGN", "TMO",
                        
                        # Consumption & Retail
                        "WMT", "COST", "TGT", "NKE", "SBUX", "EL", "LULU",
                        
                        # Energy & Industry
                        "XOM", "CVX", "GE", "CAT", "DE", "BA", "HON",
                        
                        # Auto & Transport
                        "F", "GM", "RIVN", "FDX", "UPS",
                        
                        # Tech / Cloud / Cybersecurity
                        "NOW", "ESTC", "OKTA", "FTNT", "MNTY", "ANET", "APP", "MELI"
                    ]
                    
                    # Randomly select 20 tickers to analyze this round to keep context manageable
                    # Always include current portfolio holdings to ensure we track them
                    holdings = [k for k in portfolio.keys() if "POLY" not in k and "-" not in k and k in stock_universe]
                    pool = list(set(stock_universe) - set(holdings))
                    selected_stocks = holdings + random.sample(pool, min(len(pool), 20 - len(holdings)))
                    
                    market_context_str += "\nREAL-TIME STOCK PRICES (Ticker | Price | Day Change):\n"
                    tickers = yf.Tickers(" ".join(selected_stocks))
                    
                    for symbol in selected_stocks:
                        try:
                            info = tickers.tickers[symbol].fast_info
                            price = info.last_price
                            prev_close = info.previous_close
                            change_percent = ((price - prev_close) / prev_close) * 100 if prev_close else 0.0
                            
                            indicator = "(DIP BUY OPP)" if change_percent < -1.5 else "(MOMENTUM)" if change_percent > 1.5 else "(Choppy)"
                            market_context_str += f"- {symbol} | ${price:.2f} | Day Change: {change_percent:+.2f}% {indicator} | Ticker: {symbol}\n"
                        except:
                            pass
                except Exception as e:
                    logger.error(f"Error fetching stocks: {e}")
            else:
                market_context_str += "\nStock Market: CLOSED (Trading Halted). Do NOT trade stocks.\n"
        else:
             market_context_str += "Stock Trading: DISABLED.\n"
        
        # Format Portfolio Data (Holdings)
        portfolio_str = ""
        if portfolio:
            for asset, details in portfolio.items():
                portfolio_str += f"- {asset}: {details['shares']:.2f} shares @ Avg Price ${details['avg_price']:.2f}\n"
        else:
            portfolio_str = "None (All Cash)"

        # Calculate financial state
        invested_capital = sum(v['shares'] * v['avg_price'] for v in portfolio.values()) if portfolio else 0
        total_capital = current_balance + invested_capital
        cash_percentage = (current_balance / total_capital * 100) if total_capital > 0 else 0
        
        context = f"""
        Act as a High-Stakes Speculator and Venture Trader.
        Your goal is active trading on SHORT TERM prediction markets to compound gains quickly.
        Current Date: {today_date}
        
        **MARKET STATUS**:
        - US Stocks: {"OPEN" if market_open else "CLOSED (Do NOT trade Stocks)"}
        - Crypto/Polymarket: OPEN 24/7
        
        {restriction_note}
        
        Financial Overview:
        - Total Capital: ${total_capital:.2f}
        - Cash Balance: ${current_balance:.2f} ({cash_percentage:.1f}% of capital)
        - Invested Capital: ${invested_capital:.2f}
        
        Current Portfolio Listings:\n{portfolio_str}
        
        Market Sentiment: {sentiment}
        
        {market_context_str}
        
        Analyze the market conditions. Look for "Underdogs" or "High Volatility" plays.
        Decide on ONE action: BUY, SELL, HOLD, or WATCH.
        
        
        MANDATORY STRATEGY & RULES:
        
        **1. POLYMARKET STRATEGY (Binary / Expiry Focus)**:
           - **Core Rule**: ONLY BUY if "days left" is <= 7.
           - **Goal**: Snipe mispriced binary events near expiry.
           - **Constraint**: Max price $0.75 (seek asymmetry).
           - **Naming**: `POLY:<slug>:<OUTCOME_NAME>`
        
        **2. STOCKS & CRYPTO STRATEGY (Day Trader / Scalper)**:
           - **Mindset**: High Frequency Swing Trader.
           - **Tactics**: 
             - **Dip Buying**: If Day Change is Negative (e.g. -2%), BUY to catch the rebound.
             - **Momentum**: If Day Change is strong (+3%), BUY to ride the wave.
           - **Returns**: Target small consistent gains (2-5%). Do not wait for 100% returns.
           - **Activity**: Trade frequently. Do not sit on cash.
           - **Naming**: Use Ticker (e.g., `NVDA`, `BTC-USD`).
           
        **3. Capital Allocation**: 
           - **Target**: 80% Invested / 20% Cash.
           - If Cash > 50%: **AGGRESSIVELY BUY** top stocks/crypto immediately.
           
        **4. Execution**:
           - **Price**: You MUST use the exact price listed in the context.
           - **Size**: Trade in DOLLAR AMOUNTS (e.g. $50, $100). Do NOT output share counts.
        
        Strictly output valid JSON with keys: 
        - "action": (BUY/SELL/HOLD/WATCH)
        - "asset": (String meeting the Naming criteria above)
        - "amount": (float - IN USD DOLLARS. Example: 150.0 means $150.00. Do NOT output number of shares.)
        - "price": (float, current market price)
        - "reasoning": (short punchy explanation, max 15 words)
        """
        
        if not self.valid_models:
            return self._simulate_decision()
            
        # Try models in sequence (Fallback logic)
        for model_name in self.valid_models:
            try:
                # logger.info(f"Using Gemini Model: {model_name}")
                model = genai.GenerativeModel(model_name)
                chat = model.start_chat(history=[])
                response = chat.send_message(context)
                
                cleaned_text = response.text.strip()
                if "```json" in cleaned_text:
                    cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned_text:
                    cleaned_text = cleaned_text.split("```")[1].split("```")[0].strip()
                    
                decision = json.loads(cleaned_text)
                
                # --- HARD GUARDRAILS ---
                # Enforce Max Buy Price of $0.75 ONLY for Polymarket/Prediction assets
                # We allow Stocks/Crypto (e.g. NVDA at $140) to pass through.
                if decision.get("action") == "BUY":
                    asset_name = str(decision.get("asset", ""))
                    try:
                        price = float(decision.get("price", 0))
                        
                        # Only apply limitation to Polymarket assets or low-value binary options
                        # If price is > 1.0, it's likely a stock/crypto, so we ALLOW it.
                        is_prediction_market = asset_name.startswith("POLY:") or price < 0.99
                        
                        if is_prediction_market and price > 0.75:
                            logger.warning(f"BLOCKED BUY: AI tried to buy prediction asset {asset_name} at ${price}. Limit is $0.75.")
                            decision = {
                                "action": "HOLD",
                                "asset": asset_name,
                                "amount": 0,
                                "price": price,
                                "reasoning": f"BLOCKED: Price ${price} is too high (> $0.75) for prediction markets."
                            }
                    except:
                        pass
                
                # If successful, return immediately
                return decision
                
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}. Switching to next model...")
                continue
        
        # If all models fail
        return {"action": "HOLD", "reasoning": "All models unavailable (Quota/Error)"}

    def _simulate_decision(self):
        """Fallback simulation if no API key or error - Tries to use REAL Polymarket data first"""
        actions = ['BUY', 'HOLD', 'SELL', 'WATCH']
        
        # Try to get REAL active markets first
        try:
            from polymarket import get_top_markets
            real_markets = get_top_markets(limit=5)
            if real_markets:
                # Pick a random real market
                market = random.choice(real_markets)
                asset = f"POLY:{market['slug']}" # Use the REAL slug
                # Use real price estimation from the string if possible or random
                # market['prices'] is like "Yes: 0.98, No: 0.02"
                # We'll just pick a random price for simulation context
                price = round(random.uniform(0.01, 0.99), 2)
            else:
                raise Exception("No markets found")
        except Exception as e:
            logger.warning(f"Simulation fallback using defaults due to: {e}")
            # Safe Fallback Assets (Stocks + known Crypto)
            assets = ['BTC', 'ETH', 'TSLA', 'NVDA', 'AAPL', 'MSFT']
            asset = random.choice(assets)
            price = round(random.uniform(100, 3000), 2)
        
        action = random.choice(actions)
        amount = round(random.uniform(5, 50), 2)
        
        return {
            "action": action,
            "asset": asset,
            "amount": amount,
            "price": price, 
            "reasoning": f"Simulated AI analysis based on momentum indicators for {asset}."
        }
