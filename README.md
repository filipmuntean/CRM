# Multi-Platform E-commerce CRM

A comprehensive CRM system that synchronizes product listings across **Marktplaats**, **Vinted**, **Depop**, and **Facebook Marketplace**. When a product is sold on one platform, it automatically updates on all others and logs the sale to Google Sheets for accounting.

## Features

- **Multi-Platform Sync**: Automatically sync products across 4 major platforms
- **Cross-Posting**: Post a product from Vinted to all other platforms with one click
- **Sold Item Tracking**: Automatically detect sold items and update all platforms
- **Google Sheets Integration**: Automatic accounting and sales tracking
- **Web Dashboard**: Clean, modern interface to manage everything
- **Browser Automation**: Uses Playwright for platforms without official APIs

## Architecture

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: Database ORM
- **Playwright**: Browser automation for Vinted, Depop, Facebook
- **Google Sheets API**: Accounting integration

### Integrations
- **Marktplaats**: Official OAuth2 API
- **Vinted**: Browser automation (official API requires approval)
- **Depop**: Browser automation (no public API)
- **Facebook Marketplace**: Browser automation

## Installation

### 1. Clone the repository
```bash
cd /Users/filip/ReLoomer/CRM
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
# Marktplaats API (get from https://api.marktplaats.nl)
MARKTPLAATS_CLIENT_ID=your_client_id
MARKTPLAATS_CLIENT_SECRET=your_client_secret

# Vinted credentials
VINTED_EMAIL=your_email@example.com
VINTED_PASSWORD=your_password

# Depop credentials
DEPOP_USERNAME=your_username
DEPOP_PASSWORD=your_password

# Facebook credentials
FACEBOOK_EMAIL=your_email@example.com
FACEBOOK_PASSWORD=your_password

# Google Sheets
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
```

### 5. Google Sheets Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google Sheets API and Google Drive API
4. Create a Service Account
5. Download credentials as `credentials.json`
6. Place `credentials.json` in the project root
7. Share your Google Sheet with the service account email

## Running the Application

### Start the server
```bash
python main.py
```

The dashboard will be available at: **http://localhost:8000**

## Usage

### 1. Import Existing Listings

From Vinted:
```bash
POST /api/sync/import/vinted
```

From Depop:
```bash
POST /api/sync/import/depop
```

### 2. Create and Cross-Post a Product

```python
# Create product
POST /api/products/
{
  "title": "Vintage Jacket",
  "description": "Beautiful vintage leather jacket",
  "price": 45.00,
  "brand": "Levi's",
  "size": "M",
  "condition": "good"
}

# Cross-post to all platforms
POST /api/products/{product_id}/cross-post
["marktplaats", "vinted", "depop", "facebook_marketplace"]
```

### 3. Check for Sold Items

```bash
POST /api/sync/check-sold
```

This will:
- Check all platforms for sold items
- Mark products as sold in database
- Update all other platform listings
- Add sale to Google Sheets

### 4. View Sales Analytics

```bash
GET /api/sales/stats?days=30
```

## API Endpoints

### Products
- `GET /api/products/` - List all products
- `POST /api/products/` - Create new product
- `GET /api/products/{id}` - Get product details
- `PUT /api/products/{id}` - Update product
- `POST /api/products/{id}/cross-post` - Cross-post to platforms
- `POST /api/products/{id}/mark-sold` - Mark as sold

### Sync
- `POST /api/sync/import/{platform}` - Import from platform
- `POST /api/sync/check-sold` - Check for sold items
- `POST /api/sync/all` - Sync all products
- `GET /api/sync/stats` - Get sync statistics

### Sales
- `GET /api/sales/` - List all sales
- `GET /api/sales/stats` - Get sales statistics

## Web Dashboard

The web dashboard provides:

1. **Dashboard**: Overview of products, sales, revenue, and profit
2. **Products**: Manage all your listings
3. **Sales**: View sales history and analytics
4. **Sync**: Control synchronization and view status
5. **Settings**: Configure platform credentials

## Database Schema

### Products
- Basic product information
- Status tracking (active/sold/pending)
- Images, category, brand, size, condition

### Platform Listings
- Links products to platform-specific listings
- Tracks sync status and errors
- Stores platform listing IDs

### Sales
- Records all sales transactions
- Calculates fees and net profit
- Tracks Google Sheets sync status

## Automation

You can set up automatic synchronization using cron or a task scheduler:

```bash
# Check for sold items every 15 minutes
*/15 * * * * curl -X POST http://localhost:8000/api/sync/check-sold

# Full sync every hour
0 * * * * curl -X POST http://localhost:8000/api/sync/all
```

## Security Notes

1. **Never commit `.env` file** - Contains sensitive credentials
2. **Use strong passwords** for platform accounts
3. **Keep Google credentials secure** - Service account has spreadsheet access
4. **Consider 2FA** - May need to disable or use app passwords

## Platform-Specific Notes

### Marktplaats
- Requires OAuth2 approval from Marktplaats
- Contact them at api@marktplaats.nl for access

### Vinted
- Official API exists but requires Pro account + allowlist
- Using browser automation as alternative
- May need to handle CAPTCHAs manually

### Depop
- No official public API
- Browser automation required
- Selectors may change, requiring updates

### Facebook Marketplace
- Most complex to automate
- Facebook actively prevents automation
- May require manual intervention for CAPTCHAs
- Consider using Facebook's official tools if available

## Troubleshooting

### Browser automation fails
- Ensure Playwright browsers are installed: `playwright install chromium`
- Check if running in headless mode: set `headless=False` for debugging
- Platform UI may have changed, update selectors in integration files

### Sync errors
- Check credentials in `.env`
- Verify platform accounts are active
- Look at error logs in sync status

### Google Sheets not updating
- Verify `credentials.json` is valid
- Check service account has access to spreadsheet
- Ensure APIs are enabled in Google Cloud Console

## Contributing

This is a personal project, but suggestions and improvements are welcome.

## License

MIT License - Use at your own risk. Be aware of platform Terms of Service.

## Disclaimer

This tool automates interactions with third-party platforms. Always:
- Check each platform's Terms of Service
- Use reasonable rate limits
- Don't spam or abuse the platforms
- Respect platform guidelines

The author is not responsible for any account suspensions or violations of platform ToS.
