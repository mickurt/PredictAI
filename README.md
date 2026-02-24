# Gemini AI Investment Agent

A fully autonomous financial agent that uses Google's Gemini API to manage a $100 starting portfolio. 
The agent analyzes simulated market data and executes Buy/Sell orders on stocks and Polymarket assets.

## Features
- **Autonomous Trading**: Runs analysis every 5 minutes automatically.
- **Manual Trigger**: "Run Analysis" button to force an immediate market check.
- **Real-time Dashboard**: Glassmorphism UI showing portfolio value, holdings, and transaction history.
- **Performance Tracking**: Charts for 24h, 5D, etc. (Simulated/Real-time data).
- **Gemini Integration**: Uses `google-generativeai` for decision making.

## Setup

1. **Prerequisites**
   - Node.js & npm
   - Python 3.9+

2. **API Keys**
   - Get a Gemini API Key from Google AI Studio.
   - Create a `.env` file in `backend/` based on `.env.example`:
     ```bash
     cd backend
     cp .env.example .env
     # Edit .env and add your GEMINI_API_KEY
     ```

3. **Installation & Running**
   - Simply run the start script in the root directory:
     ```bash
     chmod +x start.sh
     ./start.sh
     ```
   - This will install all dependencies and launch both the Backend (Port 8000) and Frontend (Port 3000).

4. **Access**
   - Open [http://localhost:3000](http://localhost:3000) to view your dashboard.

## Architecture
- **Backend**: FastAPI + SQLite + Python Schedule + Google Gemini
- **Frontend**: Next.js (App Router) + Recharts + Tailwind-free CSS
