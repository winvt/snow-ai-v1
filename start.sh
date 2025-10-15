#!/bin/bash

# Snowbomb Dashboard Start Script for Render
echo "🚀 Starting Snowbomb Dashboard..."

# Set environment variables if not already set
export STREAMLIT_SERVER_PORT=${PORT:-8501}
export STREAMLIT_SERVER_ADDRESS=${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}
export STREAMLIT_SERVER_HEADLESS=${STREAMLIT_SERVER_HEADLESS:-true}
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=${STREAMLIT_BROWSER_GATHER_USAGE_STATS:-false}

# Start Streamlit
echo "📊 Launching Streamlit on port $STREAMLIT_SERVER_PORT..."
streamlit run app.py \
  --server.port=$STREAMLIT_SERVER_PORT \
  --server.address=$STREAMLIT_SERVER_ADDRESS \
  --server.headless=$STREAMLIT_SERVER_HEADLESS \
  --browser.gatherUsageStats=$STREAMLIT_BROWSER_GATHER_USAGE_STATS
