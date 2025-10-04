# Rutgers Dining Hall Menu Scrapers

## Overview
Separate menu scrapers for each dining hall that scrape 2 days of menus including all meal periods (Breakfast, Lunch, Dinner, and Late Knight on weekdays).

## Scrapers

### 1. Neilson Dining Hall (`menus_neilson.py`)
- **Location Number**: 05
- **URL**: https://menuportal23.dining.rutgers.edu/FoodPronet/pickmenu.aspx
- **Output**: `exported_csvs/neilson_menus.csv`
- **Usage**: `python scrapers/menus_neilson.py`
- **Results**: ~496 items from 2 days

### 2. Livingston Dining Commons (`menus_livingston.py`)
- **Location Number**: 03
- **URL**: https://menuportal23.dining.rutgers.edu/foodpronet/pickmenu.aspx
- **Output**: `exported_csvs/livingston_menus.csv`
- **Usage**: `python scrapers/menus_livingston.py`
- **Results**: ~524 items from 2 days

### 3. The Atrium (`menus_atrium.py`)
- **Location Number**: 13
- **URL**: https://menuportal23.dining.rutgers.edu/FoodPronet/pickmenu.aspx
- **Output**: `exported_csvs/atrium_menus.csv`
- **Usage**: `python scrapers/menus_atrium.py`
- **Results**: ~454 items from 2 days

## CSV Output Format

Each CSV contains the following columns:
- **location**: Name of the dining hall
- **date**: Date in YYYY-MM-DD format
- **day_of_week**: Full day name (Monday, Tuesday, etc.)
- **meal_period**: Breakfast, Lunch, Dinner, or Late Knight
- **category**: Menu category (e.g., BAGELS, ENTREES, SALAD BAR, etc.)
- **item**: Name of the food item

## Features

- ✅ Scrapes 2 days of menus starting from today
- ✅ Handles all meal periods (Breakfast, Lunch, Dinner, Late Knight)
- ✅ Automatically skips Late Knight on weekends
- ✅ Organized by categories within each meal
- ✅ Uses Selenium + BeautifulSoup for dynamic content
- ✅ Headless browser mode for efficiency
- ✅ Automatic ChromeDriver management

## Running All Scrapers

To run all three scrapers at once:

```bash
source venv/bin/activate
python scrapers/menus_neilson.py
python scrapers/menus_livingston.py
python scrapers/menus_atrium.py
```

## Total Data Collected

- **Total Items**: ~1,474 menu items
- **Locations**: 3 dining halls
- **Days**: 2 days per location
- **Meal Periods**: 3-4 per day (depending on weekday/weekend)

## Notes

- Busch Dining Hall and Brower Commons use different page structures and are not included yet
- Each scraper is independent and can be run separately
- Scrapers use headless Chrome for efficiency
- All data is saved to the `exported_csvs/` directory
