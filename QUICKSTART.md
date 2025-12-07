# Quick Start Guide

Get your Multi-Platform CRM up and running in 10 minutes.

## Prerequisites

- Python 3.8 or higher
- Google account (for Sheets integration)
- Accounts on platforms you want to sync (Marktplaats, Vinted, Depop, Facebook)

## Step 1: Install

```bash
# Run the setup script
./setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Step 2: Configure Platforms

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
# Vinted (Required for importing from Vinted)
VINTED_EMAIL=your_email@example.com
VINTED_PASSWORD=your_password

# Depop (Required for Depop sync)
DEPOP_USERNAME=your_username
DEPOP_PASSWORD=your_password

# Facebook Marketplace (Optional)
FACEBOOK_EMAIL=your_email@example.com
FACEBOOK_PASSWORD=your_password

# Marktplaats (Optional - requires API approval)
MARKTPLAATS_CLIENT_ID=your_client_id
MARKTPLAATS_CLIENT_SECRET=your_client_secret
```

## Step 3: Google Sheets Setup

### Create Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable APIs:
   - Google Sheets API
   - Google Drive API
4. Create Service Account:
   - Go to "IAM & Admin" → "Service Accounts"
   - Click "Create Service Account"
   - Give it a name (e.g., "crm-service")
   - Skip optional steps
5. Create Key:
   - Click on the service account
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose JSON
   - Download the file
6. Rename downloaded file to `credentials.json`
7. Place it in the project root

### Create Spreadsheet

1. Create a new Google Sheet
2. Share it with the service account email (found in `credentials.json`)
3. Give it "Editor" permissions
4. Copy the Spreadsheet ID from URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit
   ```
5. Add to `.env`:
   ```
   GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
   ```

## Step 4: Run the Application

```bash
python main.py
```

Open your browser to: **http://localhost:8000**

## Step 5: Import Your First Products

### Option A: Import from Vinted

1. Click on "Sync" tab in dashboard
2. Click "Import from Platform"
3. Enter: `vinted`
4. Wait for import to complete

### Option B: Add Product Manually

1. Click on "Products" tab
2. Click "+ Add Product"
3. Fill in product details
4. Select platforms to cross-post to
5. Click "Create Product"

## Common Tasks

### Import from Vinted and Cross-Post

1. Import from Vinted (see above)
2. Go to Products tab
3. Click on a product
4. Click "Cross-post"
5. Select Depop and Facebook Marketplace
6. Click "Post"

### Check for Sold Items

1. Go to "Sync" tab
2. Click "Check for Sold Items"
3. System will scan all platforms
4. Sold items will be marked and synced to Google Sheets

### View Sales Analytics

1. Go to "Sales" tab
2. Filter by platform or date range
3. View revenue and profit breakdown

## Troubleshooting

### "Authentication failed" for Vinted/Depop/Facebook

- Double-check credentials in `.env`
- Try logging in manually first to ensure account works
- Check if 2FA is enabled (may need to disable or use app password)
- For Vinted: Ensure you have Vinted Pro account

### Google Sheets not updating

- Verify `credentials.json` is in project root
- Check spreadsheet is shared with service account
- Ensure APIs are enabled in Google Cloud Console

### Browser automation errors

- Make sure Playwright is installed: `playwright install chromium`
- Try running in non-headless mode for debugging:
  - Edit integration file (e.g., `app/integrations/vinted/client.py`)
  - Change `headless=True` to `headless=False`

### Products not syncing

- Check "Sync" tab for error messages
- Look at sync stats to see what needs attention
- Try manual sync: Click "Sync All Products"

## Next Steps

- Set up automatic syncing (see README.md for cron examples)
- Customize the dashboard (edit `templates/dashboard.html`)
- Add more product details (extend database schema)
- Configure platform-specific settings

## Tips

1. **Start Small**: Import a few products first, test the sync
2. **Monitor Regularly**: Check sync status to catch errors early
3. **Backup Data**: The SQLite database is `crm.db` - back it up regularly
4. **Rate Limits**: Don't sync too frequently - platforms may block you
5. **Manual Verification**: Always verify cross-posted listings on each platform

## Getting Help

- Check the full README.md for detailed documentation
- Review error logs in the sync status
- Try running in debug mode (set `DEBUG=True` in `.env`)

## Security Reminder

- Never commit `.env` or `credentials.json` to git
- Use strong, unique passwords
- Consider using environment-specific credentials
- Regularly rotate passwords and API keys
