#!/bin/bash

# Kill any existing processes on ports 8000 and 3000
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

echo "Starting Backend..."
cd backend
source venv/bin/activate
# Run in background
python main.py &
BACKEND_PID=$!
cd ..

echo "Starting Frontend..."
cd frontend
# Install if node_modules missing (first run)
if [ ! -d "node_modules" ]; then
    npm install
fi

# Run dev server
npm run dev &
FRONTEND_PID=$!

echo "Both services are running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"

# Trap Ctrl+C to kill both
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT

wait
