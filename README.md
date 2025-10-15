# ❄️ Snowbomb Dashboard

A comprehensive sales analytics dashboard for Snowbomb ice business using Loyverse POS data.

## 🚀 Quick Deploy to Render

### Option 1: One-Click Deploy (Recommended)

1. **Push to GitHub**: Ensure your code is in a GitHub repository
2. **Deploy to Render**:
   - Go to [render.com](https://render.com)
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect `render.yaml` and configure everything

### Option 2: Manual Deploy

1. **Create Web Service**:
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**:
   - **Name**: `snowbomb-dashboard`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true`

3. **Environment Variables**:
   ```
   LOYVERSE_TOKEN=d18826e6c76345888204b310aaca1351
   STREAMLIT_SERVER_PORT=$PORT
   STREAMLIT_SERVER_ADDRESS=0.0.0.0
   STREAMLIT_SERVER_HEADLESS=true
   STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
   ```

## 📊 Features

- **8 Analytics Sections**: Daily sales, locations, products, customers, credit, interactive data, transactions, invoices
- **Multi-Language Support**: English and Thai
- **Theme Customization**: Light/Dark mode
- **Smart Product Categorization**: Auto-categorize ice products
- **23+ Location Tracking**: Track sales across multiple event locations
- **Persistent Storage**: SQLite database with optimized tables
- **Real-time Data**: Sync with Loyverse POS API

## 🏗️ Local Development

### Prerequisites
- Python 3.9+
- pip

### Setup
```bash
# Clone repository
git clone <your-repo-url>
cd snow-ai-v1

# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run app.py
```

**Local URL**: http://localhost:8501

### Environment Variables (Optional)
Create a `.env` file for local development:

**Option 1: Use setup script**
```bash
python setup_env.py
```

**Option 2: Create manually**
```bash
# Create .env file with these contents:
LOYVERSE_TOKEN=d18826e6c76345888204b310aaca1351
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost
STREAMLIT_SERVER_HEADLESS=false
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

## 📁 Project Structure

```
snow-ai-v1/
├── app.py                 # Main Streamlit application
├── database.py            # SQLite database operations
├── utils/                 # Utility modules
│   ├── reference_data.py  # Data mapping utilities
│   └── charts.py          # Chart generation functions
├── requirements.txt       # Python dependencies
├── render.yaml           # Render deployment config
├── runtime.txt           # Python version specification
├── start.sh              # Startup script
├── setup_env.py          # Environment setup script
└── README.md             # This file
```

## 🔧 Configuration

### API Configuration
- **Loyverse API**: Automatically configured with token
- **Base URL**: `https://api.loyverse.com/v1.0/receipts`
- **Page Limit**: 250 items per request

### Database
- **Type**: SQLite (local file storage)
- **Location**: `loyverse_data.db`
- **Tables**: 10 optimized tables for receipts, customers, products, etc.
- **Persistence**: ✅ **Database persists between runs** - data is saved locally
- **Auto-creation**: Database and tables are created automatically on first run
- **Data loading**: Use "💾 Load Database" button to load cached data

## 📱 Usage

1. **Access Dashboard**: Open the deployed URL or localhost:8501
2. **Load Data**: Click "💾 Load Database" or go to Settings → "🔄 Sync All Metadata"
3. **Navigate**: Use the 8 sidebar sections to explore different analytics
4. **Customize**: Switch themes, languages, and settings in the Settings tab

## 🚨 Important Notes

### Database Persistence Behavior

**✅ Local Development (Your Computer)**:
- Database file (`loyverse_data.db`) is created automatically on first run
- All data persists between application restarts
- No data loss when you close and reopen the app
- Database grows as you sync more data from Loyverse API

**⚠️ Render Deployment**:
- **Free Tier**: Database resets on each deployment (data is lost)
- **Paid Tier**: Persistent storage available (data persists)
- **Data Sync**: Use "Sync All Metadata" button to reload data after deployment

**🔄 Data Loading Process**:
1. **First Run**: Database is empty, click "💾 Load Database" shows "No cached data"
2. **Sync Data**: Go to Settings → "🔄 Sync All Metadata" to fetch from Loyverse API
3. **Subsequent Runs**: Click "💾 Load Database" to load your cached data
4. **Data Persistence**: All synced data is saved locally and persists between runs

### API Token
- Token is configured for Snowbomb business
- For production, consider using environment variables for security

## 🛠️ Troubleshooting

**Common Issues**:
- **Port binding**: Ensure `--server.port=$PORT` in start command
- **Database**: SQLite file resets on free tier deployments
- **API errors**: Check `LOYVERSE_TOKEN` is correct
- **Build failures**: Verify `requirements.txt` has all dependencies

**Logs**: Check Render service logs for detailed error messages

## 📞 Support

For issues or questions:
1. Check Render service logs
2. Verify environment variables
3. Test API connectivity in Settings tab
4. Ensure all dependencies are installed

---

**Built with**: Streamlit, Python, SQLite, Plotly, Pandas
**Deployed on**: Render
**API**: Loyverse POS