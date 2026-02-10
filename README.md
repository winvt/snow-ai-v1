# 🐻‍❄️ Snow AI Dashboard

A comprehensive analytics dashboard for Loyverse POS data, built with Streamlit and Python.

## 🚀 Features

- **Daily Sales Analysis**: View detailed sales breakdowns by day, including receipts, net sales, and refunds.
- **Location-Based Insights**: Analyze sales performance across different store locations.
- **Product & Customer Analysis**: Deep dive into top-selling products and customer spending habits.
- **Data Management**: Robust tools to sync, import, and export data from Loyverse.
- **Multi-Language Support**: English and Thai interface.

## 📂 Project Structure

- **`app.py`**: Main Streamlit application.
- **`database.py`**: SQLite database interface.
- **`daily_briefing.py`**: Script for generating daily reports (e.g., for LINE notifications).
- **`scripts/`**: Maintenance and analysis tools.
    - **`export_sales.py`**: Export sales data to CSV for a specific date range.
    - **`import_receipts.py`**: Robust tool to import receipts from CSV/API.
    - **`init_db.py`**: Initialize the database schema.
    - **`setup_db.py`**: Create an empty database if needed.
- **`scripts/archive/`**: One-off analysis scripts (e.g., discrepancy investigations).

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.9+
- Loyverse API Token

### Local Development

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd snow-ai-v1
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**:
    Create a `.env` file in the root directory:
    ```env
    LOYVERSE_TOKEN=your_loyverse_token_here
    ```

4.  **Run the App**:
    ```bash
    ./start.sh
    # OR
    streamlit run app.py
    ```

## ☁️ Deployment (Render)

This project is configured for deployment on [Render](https://render.com).

1.  Connect your GitHub repository to Render.
2.  Select **Web Service**.
3.  Use the following settings (or let Render auto-detect from `render.yaml`):
    - **Runtime**: Python 3
    - **Build Command**: `pip install -r requirements.txt`
    - **Start Command**: `./start.sh`
4.  **Environment Variables**:
    - `LOYVERSE_TOKEN`: Your API Token.
    - `DATABASE_PATH`: `/opt/render/project/src/data/loyverse_data.db` (for persistent storage).
5.  **Persistent Disk**:
    - Mount a disk to `/opt/render/project/src/data` to persist the SQLite database across restarts.

## 📊 Data Management Tools

### Exporting Sales Data
Use the generalized export tool to get clean sales data:
```bash
python3 scripts/export_sales.py --start 2025-11-01 --end 2025-11-30 --output november_sales.csv
```

### Importing Receipts
To import receipts safely (checking for duplicates):
```bash
python3 scripts/import_receipts.py [input_csv]
```
