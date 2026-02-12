# VVP Cost Calculator

A comprehensive logistics cost calculation system for warehouse operations, built with Streamlit.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)

## 📋 Overview

The VVP (Verzamel Voorraad Pallet) Cost Calculator helps logistics companies calculate and compare costs across multiple warehouses, including:

- **Warehousing costs** (inbound, outbound, storage)
- **Labeling operations** (standard and advanced two-tier pricing)
- **Transfer logistics** (truck rates with dynamic lookup)
- **Second-leg warehousing** (multi-warehouse workflows)
- **P&L analysis** (margin calculations per customer/address)

### Key Features

✅ **Multi-warehouse Support** – Configure unlimited warehouses with custom rates  
✅ **Dynamic Labeling** – Simple/Complex label tiers (SPEDKA-compatible)  
✅ **Smart Transfer Pricing** – Excel-based lookup or fixed costs  
✅ **France Auto-Delivery** – Automatic department-based delivery cost calculation  
✅ **Customer Management** – Track customers and addresses  
✅ **Admin Panel** – Web-based configuration (no code required)  
✅ **Cloud Sync** – Optional GitHub Gist backup  
✅ **Export to Excel** – Generate detailed cost reports

---

## 🏗️ Architecture

### Tech Stack

- **Frontend:** Streamlit (Python 3.11+)
- **Data Storage:** JSON files + optional GitHub Gist sync
- **Cost Engine:** Custom calculators per warehouse type
- **Deployment:** Streamlit Community Cloud

### Project Structure

```
cost-app/
├── app.py                      # Main calculator interface
├── admin/
│   ├── app.py                  # Admin panel (standalone)
│   └── views/                  # Admin pages (add/edit/delete)
├── services/
│   ├── catalog/                # Catalog management
│   │   ├── config_manager.py  # Core CRUD operations
│   │   └── catalog_adapter.py # Format normalization
│   ├── repositories/           # Data access layer
│   ├── storage/                # Gist + Local file handling
│   └── utils/                  # ID generation, paths
├── warehouses/
│   ├── calculators/            # Cost calculation engines
│   ├── customers/              # Customer data loading
│   ├── exporters/              # Excel export logic
│   └── ui/                     # Calculator UI components
├── tools/                      # Data conversion scripts
├── data/
│   ├── catalog.json            # Main configuration database
│   ├── customers.xlsx          # Customer source data
│   ├── fr_delivery_rates.json # France delivery lookup
│   └── svz_truck_rates.json   # SVZ transfer rates
└── requirements.txt
```

---

## 🚀 Installation

### Prerequisites

- Python 3.11 or higher
- pip or uv (package manager)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/amsterdam-consumer-goods/cost-app.git
   cd cost-app
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the calculator**
   ```bash
   streamlit run app.py
   ```

4. **Run the admin panel** (optional)
   ```bash
   streamlit run admin/app.py
   ```

---

## ⚙️ Configuration

### Environment Variables

Create `.streamlit/secrets.toml` for cloud storage (optional):

```toml
# GitHub Gist Integration (optional)
GITHUB_GIST_ID = "your_gist_id_here"
GITHUB_TOKEN = "ghp_your_token_here"
GITHUB_GIST_FILENAME = "catalog.json"

# Disable Gist (use local only)
DISABLE_GIST = "false"

# Custom catalog path (optional)
CATALOG_PATH = "data/catalog.json"
```

### Catalog Structure

The `data/catalog.json` file stores all configuration:

```json
{
  "warehouses": [
    {
      "id": "nl_svz",
      "name": "SVZ Logistics NL",
      "rates": {
        "inbound": 8.5,
        "outbound": 8.5,
        "storage": 0.6,
        "order_fee": 5.0
      },
      "features": {
        "labeling": true,
        "label_costs": {
          "label": 0.03,
          "labelling": 0.0
        },
        "transfer": true,
        "transfer_mode": "excel",
        "transfer_excel": "data/svz_truck_rates.json"
      }
    }
  ],
  "customers": [
    {
      "name": "ACME Corporation",
      "addresses": ["Main St 10, Amsterdam", "Park Ave 5, Rotterdam"]
    }
  ]
}
```

---

## 💼 Usage

### For End Users (Calculator)

1. **Open the calculator:** `streamlit run app.py`
2. **Select a warehouse** from the sidebar
3. **Enter order details:**
   - Number of pallets
   - Pieces per pallet
   - Weeks in storage
4. **Configure features:**
   - Labeling (if enabled)
   - Transfer logistics (if enabled)
   - Second warehouse (if multi-warehouse workflow)
5. **Review P&L:** Select customer and address for margin analysis
6. **Export:** Download Excel report

### For Admins (Configuration)

1. **Open admin panel:** `streamlit run admin/app.py`
2. **Manage warehouses:**
   - **Add warehouse:** Configure rates, features, labeling tiers
   - **Update warehouse:** Edit existing configurations
   - **Delete warehouse:** Remove obsolete configurations
3. **Manage customers:** Add/edit customer database
4. **Advanced labeling:**
   - Enable via checkbox in warehouse config
   - Set Simple/Complex label costs
5. **Transfer configuration:**
   - **Excel mode:** Upload lookup table (pallets → truck_cost)
   - **Fixed mode:** Single transfer cost

---

## 🛠️ Development

### Code Organization

**Services Layer (data access):**
- `services/catalog/` – Facade for catalog operations
- `services/repositories/` – CRUD logic (warehouses, customers)
- `services/storage/` – Gist + Local file persistence

**Business Logic:**
- `warehouses/calculators/` – Cost calculation engines
- `warehouses/ui/` – Reusable UI components

**Admin Interface:**
- `admin/views/` – Admin CRUD pages
- `admin/views/helpers.py` – Shared utilities

### Adding a New Warehouse

1. **Create warehouse in admin panel** (no code required)
2. **Or manually edit** `data/catalog.json`
3. **Custom calculator?** Add to `warehouses/calculators/` and update `app.py`

### Data Conversion Tools

Convert Excel data to JSON format:

```bash
# Convert customer list
python tools/xlsx_to_json.py

# Convert France delivery rates
python tools/build_fr_json.py

# Convert SVZ truck rates
python tools/svz_rates_excel_to_json.py
```

### Cache Management

```python
# Clear Streamlit cache
st.cache_data.clear()
```

```powershell
# Clear Python cache (Windows)
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Force -Recurse
```

---

## 🌐 Deployment

### Streamlit Community Cloud

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Deploy to Streamlit Cloud"
   git push origin main
   ```

2. **Deploy on Streamlit:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect GitHub repository
   - Set main file: `app.py`
   - Add secrets (optional Gist config)

3. **Admin panel** (separate deployment):
   - Deploy again with main file: `admin/app.py`
   - Or use same deployment with URL parameter

### Environment Setup

**Streamlit Cloud automatically installs** from `requirements.txt`

**Secrets configuration:**
- Dashboard → App Settings → Secrets
- Paste `.streamlit/secrets.toml` content

---

## 🐛 Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'services.catalog'`

**Solution:**
```bash
# Clear cache and restart
rm -rf **/__pycache__
streamlit cache clear
```

### Encoding Errors

**Problem:** `UnicodeDecodeError` when loading catalog

**Solution:** All files now use UTF-8 encoding (fixed in v2.0)

### Decimal Input Issues

**Problem:** Cannot type intermediate decimal values (0.0 → 0.042)

**Workaround:** Type complete value directly: `0.042` (Streamlit limitation)

### Gist Sync Failures

**Problem:** `Cloud storage unavailable` warning

**Solution:**
- Check `GITHUB_GIST_ID` and `GITHUB_TOKEN` in secrets
- Verify token has `gist` scope
- App continues working with local storage

---

## 📚 Documentation

**Comprehensive inline documentation** is available in all modules:

- **Module-level docstrings:** Purpose, features, related files
- **Function docstrings:** Args, returns, examples
- **Code comments:** Complex logic only

### Key Modules Documentation

- `services/catalog/config_manager.py` – Catalog API reference
- `services/repositories/` – Data access patterns
- `admin/views/helpers.py` – Admin utilities
- `warehouses/calculators/` – Cost calculation logic

---

## 📝 Changelog

### v2.0 (2026-02-12) - Major Refactoring

- ✨ **UI reorganization:** Moved `warehouses/ui/` to `ui/` (root level)
- ✨ **Catalog module:** Created `services/catalog/` for better organization
- ✨ **Advanced labeling:** All warehouses support Simple/Complex tiers (not just SPEDKA)
- ✨ **Comprehensive docs:** Complete module-level documentation
- 🐛 **Encoding fixes:** UTF-8 everywhere
- 🐛 **Import cleanup:** Fixed circular dependencies
- 🗑️ **Archive removal:** Cleaned up legacy code

### v1.0 - Initial Release

- Basic warehouse configuration
- P&L calculator
- Admin panel
- Excel export

---

## 👥 Team

**Amsterdam Consumer Goods**  
Logistics Technology Division

**Lead Developer:** Gokce Aydin  
**Contact:** gaydin@amsterdamconsumergoods.com

---

## 📄 License

Proprietary - Amsterdam Consumer Goods © 2026

---

## 🎯 Roadmap

- [ ] Multi-currency support
- [ ] Historical cost tracking
- [ ] Batch import/export
- [ ] Role-based access control
- [ ] API for external integrations
- [ ] Mobile-responsive admin panel

---

## 🙏 Acknowledgments

Built with:
- [Streamlit](https://streamlit.io) - Interactive web apps
- [Pandas](https://pandas.pydata.org) - Data manipulation
- [OpenPyXL](https://openpyxl.readthedocs.io) - Excel handling

---

**Need help?** Check the inline documentation or contact the development team.
