import requests
from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def scrape_rutgers_events():
    """
    Scrape Rutgers events from the events page
    Extract: name, location, date/time, and link
    """
    import sys
    
    # Use the main events page and click Load More button to get all events
    urls_to_try = [
        "https://rutgers.campuslabs.com/engage/events"
    ]
    
    # Set up Chrome options for headless browsing
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    driver = None
    all_events = []
    
    try:
        # Initialize Chrome driver with ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        for url in urls_to_try:
            print(f"Trying URL: {url}")
            driver.get(url)
            
            # Wait for the page to load
            print("Waiting for events page to load...")
            time.sleep(8)  # Give more time for page to fully load
            
            # Try to find and interact with filters to show more events
            try:
                # Look for date filters or "All Events" options
                all_events_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'All Events') or contains(text(), 'All') or contains(text(), 'Show All')]")
                for button in all_events_buttons:
                    if button.is_displayed() and button.is_enabled():
                        driver.execute_script("arguments[0].click();", button)
                        print("Clicked 'All Events' button")
                        time.sleep(3)
                        break
                
                # Look for dropdown filters or date range selectors
                filter_elements = driver.find_elements(By.XPATH, "//select | //input[@type='date'] | //button[contains(@class, 'filter')]")
                if filter_elements:
                    print(f"Found {len(filter_elements)} filter elements")
                
                # Try to find and click on different category buttons
                category_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'category') or contains(@class, 'tag') or contains(text(), 'Category')]")
                for button in category_buttons[:3]:  # Try first 3 category buttons
                    try:
                        if button.is_displayed() and button.is_enabled():
                            driver.execute_script("arguments[0].click();", button)
                            print(f"Clicked category button: {button.text}")
                            time.sleep(2)
                    except:
                        continue
                
                # Try to find date range selectors
                date_selectors = driver.find_elements(By.XPATH, "//input[@type='date'] | //select[contains(@name, 'date')] | //button[contains(text(), 'Date')]")
                for selector in date_selectors[:2]:  # Try first 2 date selectors
                    try:
                        if selector.is_displayed() and selector.is_enabled():
                            driver.execute_script("arguments[0].click();", selector)
                            print(f"Clicked date selector: {selector.get_attribute('name') or selector.text}")
                            time.sleep(2)
                    except:
                        continue
                    
            except Exception as e:
                print(f"Could not interact with filters: {e}")
            
            # Wait for event cards to be present
            wait = WebDriverWait(driver, 10)
            
            # Click "LOAD MORE" button repeatedly until we get 100-150 events
            print("Starting to load more events...")
            target_events = 150
            current_events = 0
            load_more_attempts = 0
            max_attempts = 30  # Safety limit
            
            while current_events < target_events and load_more_attempts < max_attempts:
                # First, count current events - look for event links
                current_event_cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/engage/event/']")
                
                current_events = len(current_event_cards)
                print(f"Current events found: {current_events}")
                
                if current_events >= target_events:
                    print(f"Reached target of {target_events} events!")
                    break
                
                # Look for "LOAD MORE" button - try multiple selectors
                # First, let's try to find all buttons and see what's available
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                print(f"Found {len(all_buttons)} total buttons on page")
                
                # Try different selectors for Load More button
                load_more_buttons = []
                
                # Method 1: Case-insensitive text search
                load_more_buttons = driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]")
                
                if not load_more_buttons:
                    # Method 2: Direct text match
                    load_more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'LOAD MORE') or contains(text(), 'Load More') or contains(text(), 'load more')]")
                
                if not load_more_buttons:
                    # Method 3: Look for buttons with specific classes or IDs
                    load_more_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'load') or contains(@id, 'load')]")
                
                if not load_more_buttons:
                    # Method 4: Look for any button that might load more content
                    for btn in all_buttons:
                        btn_text = btn.text.lower().strip()
                        if 'load' in btn_text and 'more' in btn_text:
                            load_more_buttons.append(btn)
                            break
                
                if not load_more_buttons:
                    print("No more 'LOAD MORE' buttons found")
                    # Print first few button texts for debugging
                    for i, btn in enumerate(all_buttons[:10]):
                        try:
                            print(f"  Button {i+1}: '{btn.text}'")
                        except:
                            pass
                    break
                else:
                    print(f"Found {len(load_more_buttons)} 'LOAD MORE' button(s)")
                
                # Click the LOAD MORE button
                button_clicked = False
                for button in load_more_buttons:
                    try:
                        if button.is_displayed() and button.is_enabled():
                            # Scroll to the button
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                            time.sleep(1)
                            
                            # Click the button
                            driver.execute_script("arguments[0].click();", button)
                            print(f"Clicked 'LOAD MORE' button (attempt {load_more_attempts + 1})")
                            button_clicked = True
                            break
                    except Exception as e:
                        print(f"Error clicking button: {e}")
                        continue
                
                if not button_clicked:
                    print("Could not click LOAD MORE button, trying to find it again...")
                    # Sometimes the button needs a moment to become clickable
                    time.sleep(2)
                    continue
                
                # Wait 5 seconds for new events to load
                print("Waiting 5 seconds for new events to load...")
                time.sleep(5)
                
                load_more_attempts += 1
            
            print(f"Finished loading events. Total LOAD MORE clicks: {load_more_attempts}")
            
            # Look for event cards - based on the HTML structure you provided
            # The structure is: <a href="/engage/event/..."> containing the event card
            event_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/engage/event/']")
            
            print(f"Found {len(event_links)} event cards on this page")
            
            # Process events from this page
            for event_link in event_links:
                try:
                    event_data = {}
                    
                    # Extract event link
                    href = event_link.get_attribute('href')
                    if not href or '/engage/event/' not in href:
                        continue
                    event_data['link'] = href
                    
                    # Extract event name (from h3 tag inside the link)
                    try:
                        name_element = event_link.find_element(By.TAG_NAME, "h3")
                        event_data['name'] = name_element.text.strip()
                    except:
                        # If h3 not found, skip this event
                        continue
                    
                    # Extract date and time - look for the SVG calendar icon and the text next to it
                    try:
                        # Get all the text content from the event card
                        card_html = event_link.get_attribute('innerHTML')
                        all_text = event_link.text
                        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                        
                        date_time = "TBD"
                        location = "TBD"
                        
                        # Find date/time (contains day name and AM/PM/EDT/EST)
                        for i, line in enumerate(lines):
                            # Check if this line contains date/time information
                            if any(day in line for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']):
                                if any(time_indicator in line for time_indicator in ['AM', 'PM', 'EDT', 'EST', 'at ']):
                                    date_time = line
                                    # The next line after date is usually location
                                    if i + 1 < len(lines):
                                        potential_location = lines[i + 1]
                                        # Make sure it's not organization name or other metadata
                                        if (potential_location and 
                                            potential_location != event_data['name'] and
                                            not any(word in potential_location.lower() for word in ['ended', 'minutes ago', 'hours ago', 'days ago']) and
                                            len(potential_location) > 2):
                                            location = potential_location
                                    break
                        
                        event_data['date_time'] = date_time
                        event_data['location'] = location
                        
                    except Exception as e:
                        event_data['date_time'] = "TBD"
                        event_data['location'] = "TBD"
                    
                    # Only add if we have meaningful data and not already collected
                    if (event_data['name'] and 
                        event_data['link'] and
                        not any(existing['link'] == event_data['link'] for existing in all_events)):
                        all_events.append(event_data)
                        print(f"Found event #{len(all_events)}: {event_data['name']}")
                    
                except Exception as e:
                    print(f"Error processing event card: {e}")
                    continue
        
        return all_events
        
    except Exception as e:
        print(f"Error with Selenium: {e}")
        return []
    finally:
        if driver:
            driver.quit()

def export_events_to_csv(events, filename='rutgers_events.csv'):
    """
    Export events data to CSV file
    """
    if not events:
        print("No events data to export")
        return
    
    # Create fieldnames for CSV
    fieldnames = ['name', 'location', 'date_time', 'link']
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for event in events:
            writer.writerow(event)
    
    print(f"Events data exported to {filename}")
    print(f"Total events found: {len(events)}")

def main():
    """
    Main function to scrape and export events
    """
    print("Scraping Rutgers Events...")
    events = scrape_rutgers_events()
    
    if events:
        print(f"Found {len(events)} events:")
        for event in events:
            print(f"- {event['name']} at {event['location']} on {event['date_time']}")
        
        # Export to CSV
        export_events_to_csv(events)
    else:
        print("No events found")

if __name__ == "__main__":
    main()
