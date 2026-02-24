import requests
import json
import logging

logger = logging.getLogger(__name__)

GAMMA_API_URL = "https://gamma-api.polymarket.com/events"

def get_top_markets(limit=10):
    """
    Fetches a mix of:
    1. Top active markets by volume.
    2. Markets ending soon (Short Term).
    """
    market_data = {}

    def fetch_markets(params, tag_prefix=""):
        try:
            # Common params
            base_params = {
                "closed": "false",
                "limit": limit,
                "active": "true" 
            }
            base_params.update(params)
            
            response = requests.get(GAMMA_API_URL, params=base_params, timeout=10)
            response.raise_for_status()
            events = response.json()

            for event in events:
                title = event.get('title')
                slug = event.get('slug')
                volume = float(event.get('volume', 0) or 0)
                end_date_raw = event.get('endDate')
                
                # Format Date
                end_date_str = "Unknown"
                if end_date_raw:
                    try:
                        # Simple truncation or parsing
                        end_date_str = end_date_raw.split('T')[0]
                    except:
                        end_date_str = str(end_date_raw)

                # Deduplicate by slug immediately
                if slug in market_data:
                    continue

                markets = event.get('markets', [])
                if not markets:
                    continue
                
                # Use the first market
                main_market = markets[0]
                if main_market.get('closed'):
                    continue

                # Parse prices
                try:
                    raw_prices = json.loads(main_market.get("outcomePrices", "[]"))
                    outcomes = json.loads(main_market.get("outcomes", "[]"))
                except:
                    continue

                if not raw_prices or not outcomes:
                    continue

                # Format prices
                price_list = []
                for out, price in zip(outcomes, raw_prices):
                    price_list.append(f"{out}: {price}")
                price_str = ", ".join(price_list)
                
                # Add tag if provided
                display_title = f"{tag_prefix} {title}" if tag_prefix else title

                market_data[slug] = {
                    "title": display_title,
                    "slug": slug,
                    "volume": volume,
                    "prices": price_str,
                    "deadline": end_date_str
                }
        except Exception as e:
            logger.error(f"Error fetching Polymarket data with params {params}: {e}")

    # 1. Fetch High Volume
    fetch_markets({"order": "volume", "ascending": "false"})

    # 2. Fetch Closing Soon (Short Term)
    # sorting by endDate ascending gives soonest expiring
    fetch_markets({"order": "endDate", "ascending": "true"}, tag_prefix="[Short Term]")
    
    return list(market_data.values())

if __name__ == "__main__":
    # Test run
    data = get_top_markets(5)
    print(json.dumps(data, indent=2))
