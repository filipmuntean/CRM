# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-platform e-commerce CRM that synchronizes product listings across Marktplaats, Vinted, Depop, and Facebook Marketplace. When a product is sold on one platform, it updates all others and logs to Google Sheets.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run the server (http://localhost:8000)
python main.py

# Run tests
pytest

# Linting and formatting
black .
flake8
```

## Architecture

### Core Structure
- `main.py` - FastAPI app entry point, mounts routers and static files
- `app/core/config.py` - Pydantic settings loaded from `.env`
- `app/core/database.py` - SQLAlchemy setup with SQLite default

### API Layer (`app/api/`)
Three routers mounted at `/api`:
- `products.py` - CRUD operations, cross-posting to platforms
- `sync.py` - Import from platforms, check sold items, sync all
- `sales.py` - Sales listing and statistics

### Models (`app/models/`)
- `Product` - Core product with status (active/sold/pending/inactive)
- `PlatformListing` - Links products to platform-specific listings, tracks sync status
- `Sale` - Records transactions, fees, and Google Sheets sync status

### Platform Integrations (`app/integrations/`)
- `base.py` - `BasePlatformIntegration` abstract class defining the interface
- Each platform has its own subdirectory (marktplaats, vinted, depop, facebook_marketplace)
- Marktplaats uses OAuth2 API; others use Playwright browser automation

### Services (`app/services/`)
- `sync_service.py` - Orchestrates cross-platform synchronization
- `sheets_service.py` - Google Sheets accounting integration

### Key Patterns
- Platform integrations implement `BasePlatformIntegration` with methods: `authenticate`, `get_listings`, `create_listing`, `update_listing`, `delete_listing`, `mark_as_sold`, `get_sales`, `check_listing_status`
- Database sessions use FastAPI dependency injection via `get_db()`
- Configuration flows from `.env` → `Settings` class → `settings` singleton
