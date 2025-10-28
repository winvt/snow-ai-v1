# 🐻‍❄️ Snow AI Dashboard

A comprehensive sales analytics dashboard for Snowbomb ice business using Loyverse POS data with password protection and persistent data storage.

## 🔐 Access

**Password**: `snowbomb`

## 🚀 Quick Deploy to Render

### One-Click Deploy (Recommended)

1. **Push to GitHub**: Ensure your code is in a GitHub repository
2. **Deploy to Render**:
   - Go to [render.com](https://render.com)
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect `render.yaml` and configure everything

### Manual Deploy

1. **Create Web Service**:
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**:
   - **Name**: `snow-ai`
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
   DATABASE_PATH=/opt/render/project/src/data/loyverse_data.db
   ```

## 📊 Features

### 🔐 Security
- **Password Protection**: Login required with password `snowbomb`
- **Session Management**: Secure authentication with logout functionality
- **Protected Access**: All dashboard features require authentication

### 📈 Analytics Sections (8 Tabs)
- **📅 Daily Sales**: Overview, trends, and KPIs
- **📍 By Location**: Location-specific sales analysis
- **📦 By Product**: Product performance and categorization
- **👥 By Customer**: Customer analytics and behavior
- **💳 Credit**: Credit vs cash sales analysis
- **📊 Interactive Data**: Filterable data exploration
- **📋 Transaction Log**: Detailed transaction history
- **🧾 Customer Invoice**: Customer-specific invoice generation
- **🧊 Ice Forecast**: Demand forecasting and trends
- **👥 CRM**: Customer relationship management

### 🌐 Multi-Language Support
- **English** and **Thai** language support
- **Dynamic Translation**: All UI elements translated
- **Language Switching**: Toggle between languages in sidebar

### 🎨 Customization
- **Theme Support**: Light/Dark mode
- **Font Sizes**: Small, Medium, Large options
- **Compact Mode**: Condensed layout option
- **Responsive Design**: Works on all screen sizes

### 🏪 Business Intelligence
- **Smart Product Categorization**: Auto-categorize ice products
- **23+ Location Tracking**: Track sales across multiple event locations
- **Real-time Data Sync**: Sync with Loyverse POS API
- **Persistent Storage**: SQLite database with optimized tables

### 💰 Advanced Sales Logic
- **Net Sales Calculation**: `receipt_total - receipt_discount`
- **Refund Handling**: Proper negative values for refunds
- **Timezone Support**: GMT+7 (Bangkok) for UI, UTC for API
- **Smart Sync**: Only fetch new data since last sync

## 🏗️ Local Development

### Prerequisites
- Python 3.9+
- pip

### Setup
```bash
# Clone repository
git clone https://github.com/winvt/snow-ai-v1.git
cd snow-ai-v1

# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run app.py
```

**Local URL**: http://localhost:8501

### Environment Variables (Optional)
Create a `.env` file for local development:

```bash
# Create .env file with these contents:
LOYVERSE_TOKEN=d18826e6c76345888204b310aaca1351
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost
STREAMLIT_SERVER_HEADLESS=false
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
DATABASE_PATH=./data/loyverse_data.db
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
└── README.md             # This file
```

## 🔧 Configuration

### API Configuration
- **Loyverse API**: Automatically configured with token
- **Base URL**: `https://api.loyverse.com/v1.0/receipts`
- **Page Limit**: 250 items per request
- **Timezone**: UTC for API calls, GMT+7 for display

### Database
- **Type**: SQLite (local file storage)
- **Location**: `loyverse_data.db` (local) or persistent disk (Render)
- **Tables**: 10 optimized tables for receipts, customers, products, etc.
- **Persistence**: ✅ **Database persists between runs** - data is saved locally
- **Auto-creation**: Database and tables are created automatically on first run
- **Data loading**: Use "💾 Load Database" button to load cached data

### Persistent Storage (Render)
- **Persistent Disk**: 1GB allocated for database storage
- **Path**: `/opt/render/project/src/data/loyverse_data.db`
- **Survives Deployments**: Data persists between deployments
- **No Data Loss**: No need to re-sync after deployments

## 📱 Usage

### First Time Setup
1. **Access Dashboard**: Open the deployed URL or localhost:8501
2. **Login**: Enter password `snowbomb`
3. **Load Data**: Click "💾 Load Database" or go to Settings → "🔄 Sync All Metadata"
4. **Navigate**: Use the 8 sidebar sections to explore different analytics

### Daily Usage
1. **Login**: Enter password to access dashboard
2. **Load Data**: Click "💾 Load Database" to load cached data
3. **Select Date Range**: Use date selectors to filter data
4. **Explore Analytics**: Navigate through different tabs
5. **Logout**: Click "🚪 Logout" when finished

## 🚨 Important Notes

### Database Persistence Behavior

**✅ Local Development (Your Computer)**:
- Database file (`loyverse_data.db`) is created automatically on first run
- All data persists between application restarts
- No data loss when you close and reopen the app
- Database grows as you sync more data from Loyverse API

**✅ Render Deployment (Paid Tier)**:
- **Persistent Disk**: Database survives deployments and restarts
- **No Data Loss**: All synced data persists between deployments
- **Fast Startup**: No need to re-sync data after deployments

**🔄 Data Loading Process**:
1. **First Run**: Database is empty, click "💾 Load Database" shows "No cached data"
2. **Sync Data**: Go to Settings → "🔄 Sync All Metadata" to fetch from Loyverse API
3. **Subsequent Runs**: Click "💾 Load Database" to load your cached data
4. **Data Persistence**: All synced data is saved locally and persists between runs

### Security
- **Password Protection**: All access requires password `snowbomb`
- **Session Management**: Authentication persists during session
- **Logout**: Clear session and return to login screen

### API Token
- Token is configured for Snowbomb business
- For production, consider using environment variables for security

## 🛠️ Troubleshooting

**Common Issues**:
- **Login Issues**: Ensure password is exactly `snowbomb`
- **Port binding**: Ensure `--server.port=$PORT` in start command
- **Database**: SQLite file persists on paid tier deployments
- **API errors**: Check `LOYVERSE_TOKEN` is correct
- **Build failures**: Verify `requirements.txt` has all dependencies

**Logs**: Check Render service logs for detailed error messages

## 📞 Support

For issues or questions:
1. Check Render service logs
2. Verify environment variables
3. Test API connectivity in Settings tab
4. Ensure all dependencies are installed
5. Verify password is correct (`snowbomb`)

## 🔄 Recent Updates

### v2.0 - Major Updates
- ✅ Added password authentication system
- ✅ Fixed all KeyError issues (79 signed_net implementations)
- ✅ Implemented proper net sales calculation with refund handling
- ✅ Added timezone handling (GMT+7 UI, UTC API)
- ✅ Enhanced smart sync with exact timestamp ranges
- ✅ Added persistent disk configuration for Render
- ✅ Cleaned up redundant files and optimized code

---

**Built with**: Streamlit, Python, SQLite, Plotly, Pandas  
**Deployed on**: Render  
**API**: Loyverse POS  
**Security**: Password Protected
