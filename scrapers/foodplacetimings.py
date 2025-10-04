"""
Rutgers Dining Scraper - Essential Data Only
Extracts 4 fields from https://food.rutgers.edu/places-eat:
1. Campus
2. Name
3. Hours
4. Meal Swipe (Yes/No)
"""

import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import json

class EssentialDiningScraper:
    def __init__(self):
        self.url = "https://food.rutgers.edu/places-eat"
        self.driver = None
        self.locations = []
    
    def setup_driver(self):
        """Setup Selenium Chrome driver"""
        print("🔧 Setting up browser...")
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        print("✅ Browser ready\n")
    
    def scrape(self):
        """Main scraping method"""
        print("="*70)
        print("🎯 RUTGERS DINING SCRAPER - ESSENTIAL DATA")
        print("="*70)
        print(f"📍 {self.url}\n")
        
        try:
            self.setup_driver()
            
            # Load page
            print("📥 Loading page...")
            self.driver.get(self.url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)
            
            # Scroll multiple times to ensure all content loads
            print("📜 Scrolling to load all content...")
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            for i in range(5):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Parse HTML
            print("🔍 Extracting data...\n")
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            
            # Extract locations
            self._extract_all_locations(soup)
            
            print(f"\n✅ Found {len(self.locations)} locations!\n")
            return True
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.driver:
                self.driver.quit()
    
    def _extract_all_locations(self, soup):
        """Extract all dining locations with their essential info"""
        # Blacklist non-restaurant entries
        blacklist = [
            'catering', 'tour', 'faculty', 'staff', 'retail dining menus',
            'express overview', 'sustainability', 'manage account',
            'participating locations', 'catering menu', 'add money',
            'meal plans', 'dining dollars', 'scarlet bucks'
        ]

        seen = set()

        # Find main content area
        main_content = soup.find('main') or soup.find('body')
        if not main_content:
            print("❌ Could not find main content")
            return

        # Find campus headers in order
        campus_headers = []
        for tag in main_content.find_all(['h2', 'h3']):
            txt = tag.get_text(' ', strip=True).lower()
            if 'campus' in txt:
                campus_headers.append(tag)

        # If no campus headers found, fallback to scanning entire main content
        if not campus_headers:
            campus_headers = [main_content]

        # Iterate each campus header and collect content until next campus header
        for idx, ch in enumerate(campus_headers):
            ch_text = ch.get_text(' ', strip=True)
            low = ch_text.lower()
            if 'busch' in low:
                campus = 'Busch'
            elif 'livingston' in low:
                campus = 'Livingston'
            elif 'college avenue' in low or 'college-avenue' in low or 'college ave' in low:
                campus = 'College Avenue'
            elif 'cook' in low or 'douglass' in low:
                campus = 'Cook/Douglass'
            else:
                campus = 'Unknown'

            print(f"\n📍 Processing {campus} Campus...")

            # Collect siblings until next campus header
            section_nodes = []
            for sib in ch.next_siblings:
                if getattr(sib, 'name', None) in ['h2', 'h3'] and sib in campus_headers:
                    break
                # Only consider Tag nodes
                if getattr(sib, 'get_text', None):
                    section_nodes.append(sib)

            # Build a combined soup fragment for this campus
            # Search for location headers inside the section nodes
            for node in section_nodes:
                # Skip nodes that look like navigation or meta content
                node_text = node.get_text(' ', strip=True).lower()
                if any(b in node_text for b in blacklist):
                    continue

                # Find candidate headers inside node
                # Prefer elements that visually correspond to accordion headers
                candidates = []
                candidates.extend(node.find_all(['h3', 'h4']))
                # also consider clickable buttons/anchors inside
                candidates.extend(node.find_all(['button', 'a']))

                for header in candidates:
                    name = header.get_text(' ', strip=True)
                    if not name or len(name) < 2:
                        continue

                    name_clean = re.sub(r"\s*[-–]\s*meal swipe eligible", '', name, flags=re.IGNORECASE).strip()
                    name_clean = re.sub(r"\(.*?Campus.*?\)", '', name_clean, flags=re.IGNORECASE).strip()
                    name_clean = re.sub(r"\s+", ' ', name_clean).strip()

                    # Filter generic and blacklisted names
                    generic = ['places to eat', 'dining options', 'hours', 'locations', 'menu', 'faculty dining options']
                    if name_clean.lower() in generic:
                        continue
                    if any(b in name_clean.lower() for b in blacklist):
                        continue
                    if name_clean in seen:
                        continue

                    # Try to find the detail panel for this header
                    block = None
                    # First try: next sibling panel
                    nxt = header.find_next_sibling()
                    if nxt and getattr(nxt, 'get_text', None):
                        block = nxt
                    else:
                        # fallback: parent block
                        block = header.find_parent(['article', 'section', 'div', 'li'])

                    if not block:
                        continue

                    block_text = block.get_text(' ', strip=True)

                    # Ensure this block seems like a food entry (has time ranges or 'meal' or 'cafe' or 'dining')
                    if not re.search(r'\d{1,2}:\d{2}\s*[ap]m', block_text, re.IGNORECASE) and \
                       not any(k in block_text.lower() for k in ['meal', 'cafe', 'dining', 'truck', 'panera', 'starbucks', 'pizza', 'burger', 'sbarro', 'qdo']) :
                        # skip non-food content
                        continue

                    hours = self._extract_hours(block_text)
                    meal_swipe = self._check_meal_swipe(name, block_text)

                    loc = {
                        'campus': campus,
                        'name': name_clean,
                        'hours': hours,
                        'meal_swipe': meal_swipe
                    }

                    self.locations.append(loc)
                    seen.add(name_clean)

                    print(f"   ✓ {name_clean}")
                    if hours != 'Hours not available':
                        print(f"      Hours: {hours[:80]}...")
                    print(f"      Meal Swipe: {meal_swipe}")
    
    def _extract_hours(self, text):
        """Extract operating hours from text"""
        hours_list = []
        
        # Comprehensive patterns for hours
        patterns = [
            # Weekday patterns
            (r'Weekdays?[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Weekdays'),
            (r'Mon(?:day)?[\s-]*(?:to|thru|through)?[\s-]*Thu(?:rs?(?:day)?)?[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Mon-Thu'),
            (r'Mon(?:day)?[\s-]*(?:to|thru|through)?[\s-]*Fri(?:day)?[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Mon-Fri'),
            
            # Weekend patterns
            (r'Weekends?[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Weekends'),
            (r'Sat(?:urday)?[\s-]*(?:to|and|&)?[\s-]*Sun(?:day)?[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Sat-Sun'),
            
            # Individual days
            (r'Monday[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Monday'),
            (r'Tuesday[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Tuesday'),
            (r'Wednesday[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Wednesday'),
            (r'Thursday[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Thursday'),
            (r'Friday[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Friday'),
            (r'Saturday[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Saturday'),
            (r'Sunday[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Sunday'),
            
            # Breakfast, Lunch, Dinner patterns
            (r'Breakfast[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Breakfast'),
            (r'Lunch[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Lunch'),
            (r'Dinner[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Dinner'),
            
            # Open/Hours pattern
            (r'(?:Open|Hours)[:\s]*(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)', 'Hours'),
        ]
        
        for pattern, label in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                time_str = match.group(1).strip()
                # Normalize the time string
                time_str = re.sub(r'\s+', ' ', time_str)
                time_str = re.sub(r'([ap])\.?m\.?', r'\1m', time_str, flags=re.IGNORECASE)
                hours_list.append(f"{label}: {time_str}")
        
        # If no specific patterns found, look for any time ranges
        if not hours_list:
            generic_time = re.findall(r'\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?', text, re.IGNORECASE)
            if generic_time:
                for time_str in generic_time[:3]:  # Limit to first 3 matches
                    time_str = re.sub(r'\s+', ' ', time_str.strip())
                    time_str = re.sub(r'([ap])\.?m\.?', r'\1m', time_str, flags=re.IGNORECASE)
                    hours_list.append(time_str)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_hours = []
        for h in hours_list:
            if h not in seen:
                seen.add(h)
                unique_hours.append(h)
        
        return ' | '.join(unique_hours) if unique_hours else 'Hours not available'
    
    def _check_meal_swipe(self, name, text):
        """Check if meal swipes are accepted"""
        combined = (name + ' ' + text).lower()
        
        meal_indicators = [
            'meal swipe eligible',
            'meal swipe',
            'meal swipes accepted',
            'accepts meal swipes',
            'meal plan',
            'swipe eligible'
        ]
        
        for indicator in meal_indicators:
            if indicator in combined:
                return 'Yes'
        
        return 'No'
    
    def save_to_csv(self, filename='rutgers_dining_essential.csv'):
        """Save to CSV"""
        if not self.locations:
            print("❌ No data to save")
            return
        
        df = pd.DataFrame(self.locations)
        df = df[['campus', 'name', 'hours', 'meal_swipe']]  # Ensure column order
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"💾 Saved to {filename}")
    
    def save_to_json(self, filename='rutgers_dining_essential.json'):
        """Save to JSON"""
        if not self.locations:
            print("❌ No data to save")
            return
        
        data = {
            'scraped_at': datetime.now().isoformat(),
            'total_locations': len(self.locations),
            'locations': self.locations
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved to {filename}")
    
    def save_to_excel(self, filename='rutgers_dining_essential.xlsx'):
        """Save to Excel"""
        if not self.locations:
            print("❌ No data to save")
            return
        
        df = pd.DataFrame(self.locations)
        df = df[['campus', 'name', 'hours', 'meal_swipe']]
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # All locations
            df.to_excel(writer, sheet_name='All Locations', index=False)
            
            # Format columns
            ws = writer.sheets['All Locations']
            ws.column_dimensions['A'].width = 20  # Campus
            ws.column_dimensions['B'].width = 40  # Name
            ws.column_dimensions['C'].width = 60  # Hours
            ws.column_dimensions['D'].width = 12  # Meal Swipe
            
            # By campus
            by_campus = df.groupby('campus').size().reset_index(name='count')
            by_campus.columns = ['Campus', 'Total Locations']
            by_campus.to_excel(writer, sheet_name='By Campus', index=False)
            
            # Meal swipe only
            meal_swipe = df[df['meal_swipe'] == 'Yes'].copy()
            meal_swipe.to_excel(writer, sheet_name='Meal Swipe Locations', index=False)
        
        print(f"💾 Saved to {filename}")
    
    def print_summary(self):
        """Print summary of scraped data"""
        if not self.locations:
            print("❌ No data to display")
            return
        
        print("="*70)
        print("📊 SUMMARY")
        print("="*70)
        print(f"Total Locations: {len(self.locations)}")
        
        # By campus
        by_campus = {}
        for loc in self.locations:
            campus = loc['campus']
            by_campus[campus] = by_campus.get(campus, 0) + 1
        
        print("\nBy Campus:")
        for campus, count in sorted(by_campus.items()):
            print(f"  • {campus}: {count}")
        
        # Meal swipe
        meal_count = sum(1 for loc in self.locations if loc['meal_swipe'] == 'Yes')
        print(f"\nMeal Swipe Eligible: {meal_count}")
        
        # Hours available
        hours_count = sum(1 for loc in self.locations if loc['hours'] != 'Hours not available')
        print(f"With Hours Information: {hours_count}")
        
        print("="*70 + "\n")
    
    def print_data(self):
        """Print all scraped data"""
        if not self.locations:
            print("❌ No data to display")
            return
        
        print("\n" + "="*70)
        print("📋 ALL LOCATIONS")
        print("="*70)
        
        current_campus = None
        for loc in self.locations:
            if loc['campus'] != current_campus:
                current_campus = loc['campus']
                print(f"\n{'='*70}")
                print(f"📍 {current_campus.upper()} CAMPUS")
                print(f"{'='*70}")
            
            print(f"\n🍽️  {loc['name']}")
            print(f"   ⏰ {loc['hours']}")
            print(f"   💳 Meal Swipe: {loc['meal_swipe']}")

def main():
    """Main execution"""
    print("\n" + "="*70)
    print("🎯 RUTGERS DINING SCRAPER - ESSENTIAL DATA")
    print("="*70 + "\n")
    
    print("Will extract ONLY:")
    print("  1. Campus")
    print("  2. Name")
    print("  3. Hours")
    print("  4. Meal Swipe (Yes/No)\n")
    
    input("Press ENTER to start...")
    
    scraper = EssentialDiningScraper()
    
    if scraper.scrape():
        scraper.print_summary()
        
        # Ask if user wants to see all data
        show = input("\nShow all extracted data? (y/n): ").strip().lower()
        if show == 'y':
            scraper.print_data()
        
        print("\n" + "="*70)
        print("Save as:")
        print("1. CSV")
        print("2. JSON")
        print("3. Excel")
        print("4. All formats")
        
        choice = input("\nChoice (1-4): ").strip()
        
        print()
        if choice == '1':
            scraper.save_to_csv()
        elif choice == '2':
            scraper.save_to_json()
        elif choice == '3':
            scraper.save_to_excel()
        else:
            scraper.save_to_csv()
            scraper.save_to_json()
            scraper.save_to_excel()
        
        print("\n✅ Done!\n")
    else:
        print("\n❌ Scraping failed\n")

if __name__ == "__main__":
    main()