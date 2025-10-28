# Data Directory for Persistent Storage

This directory contains the SQLite database file that will be mounted as a persistent disk on Render.

## Files:
- loyverse_data.db: Main database file with all sales data

## Mount Path on Render:
- /opt/render/project/src/data

## Environment Variable:
- DATABASE_PATH=/opt/render/project/src/data/loyverse_data.db

This ensures data persists between deployments and restarts.
