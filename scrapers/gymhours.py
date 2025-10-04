import requests
from bs4 import BeautifulSoup
import re
import csv


def fetch_gym_hours():
    """Fetch raw gym hours data from Rutgers Recreation website"""
    
    url = "https://recreation.rutgers.edu/operating-status"
    
    print("Fetching gym hours page...")
    response = requests.get(url)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the main content area
    print("\n" + "="*80)
    print("RAW GYM HOURS DATA")
    print("="*80)
    
    # Extract Fall Semester Hours section
    print("\n--- FALL SEMESTER HOURS ---")
    fall_hours = soup.find_all('li')
    
    for item in fall_hours:
        text = item.get_text(strip=True)
        # Filter for gym-related items
        if any(gym in text for gym in ['College Avenue Gym', 'Cook/Douglass', 'Livingston', 
                                        'Rutgers Fitness Center', 'Sonny Werblin']):
            print(f"  {text}")
    
    # Extract Game Day schedules
    print("\n--- FOOTBALL GAME DAY SCHEDULES ---")
    
    # Find all text after the game day header
    all_text = soup.get_text()
    
    # Look for the game day section
    if "RU Home Football Game Day" in all_text:
        lines = all_text.split('\n')
        capture = False
        
        for line in lines:
            line = line.strip()
            if "RU Home Football Game Day" in line:
                capture = True
                continue
            if capture and line:
                # Stop at the next major section
                if "Room-Specific Hours" in line or "Adverse Weather" in line:
                    break
                print(f"  {line}")
    
    print("\n" + "="*80)
    return soup


def parse_gym_hours(soup):
    """Parse and clean gym hours data into structured format"""
    
    gym_data = []
    
    # Pattern to match gym hours lines
    gym_pattern = r'^(.+?):\s*(.+)$'
    
    # Campus mapping
    campus_map = {
        'Sonny Werblin Recreation Center': 'Busch',
        'College Avenue Gym': 'College Avenue',
        'Livingston Recreation Center': 'Livingston',
        'Cook/Douglass Recreation Center': 'Cook/Douglass',
        'Rutgers Fitness Center @ Easton Ave': 'Off Campus'
    }
    
    # Find all list items and paragraph tags (Sonny Werblin is in a <p> tag)
    all_items = soup.find_all('li') + soup.find_all('p')
    
    print("\n" + "="*80)
    print("PARSED GYM HOURS DATA")
    print("="*80)
    
    # Parse regular fall semester hours
    print("\n--- REGULAR FALL SEMESTER HOURS ---")
    
    regular_gyms_found = set()
    
    for item in all_items:
        text = item.get_text(strip=True)
        
        # Match specific gym names with their hours
        if re.search(gym_pattern, text):
            # Check if this is a gym hours line
            gym_names = [
                'College Avenue Gym',
                'Cook/Douglass Recreation Center',
                'Livingston Recreation Center',
                'Rutgers Fitness Center @ Easton',
                'Sonny Werblin Recreation Center'
            ]
            
            matched_gym = None
            for gym in gym_names:
                if gym in text:
                    matched_gym = gym
                    break
            
            if matched_gym:
                # Skip if we already processed this gym (avoid duplicates from game day section)
                if matched_gym in regular_gyms_found:
                    continue
                
                # Don't include lines with "RU Football" as they're duplicates
                if 'RU Football' in text:
                    continue
                    
                match = re.match(gym_pattern, text)
                if match:
                    gym_name = match.group(1).strip()
                    hours_string = match.group(2).strip()
                    
                    # Remove the RU Football disclaimer if present (handles "9PMRU Football..." pattern)
                    hours_string = re.sub(r'(AM|PM)RU\s*Football.*$', r'\1', hours_string).strip()
                    
                    # Only process if it has full week schedule (contains M-Th or similar patterns)
                    if re.search(r'M-', hours_string) and re.search(r'[A-Z]{1,2}\s+\d', hours_string):
                        print(f"\n  Gym: {gym_name}")
                        print(f"  Raw Hours: {hours_string}")
                        
                        regular_gyms_found.add(matched_gym)
                        
                        # Parse individual day hours
                        day_schedule = parse_hours_string(hours_string)
                        
                        for day, hours in day_schedule.items():
                            print(f"    - {day}: {hours}")
                            gym_data.append({
                                'gym_name': gym_name,
                                'campus': campus_map.get(gym_name, 'Unknown'),
                                'schedule_type': 'Regular Fall Hours',
                                'day': day,
                                'hours': hours
                            })
    
    print("\n" + "="*80)
    return gym_data


def parse_hours_string(hours_string):
    """Parse hours string like 'M-Th 7AM-11PM, F 7AM-9PM' into individual days"""
    
    schedule = {}
    
    # Day mapping
    day_map = {
        'M': 'Monday',
        'Tu': 'Tuesday', 
        'W': 'Wednesday',
        'Th': 'Thursday',
        'F': 'Friday',
        'SA': 'Saturday',
        'SU': 'Sunday'
    }
    
    # Pattern to match day ranges and single days with their hours
    # Matches: "M-Th 7AM-11PM" or "F 7AM-9PM" or "SA Closed"
    pattern = r'([A-Z][A-Za-z]*(?:-[A-Z][A-Za-z]*)?)\s+([^,]+)'
    
    matches = re.findall(pattern, hours_string)
    
    for day_range, hours in matches:
        hours = hours.strip()
        
        # Handle day ranges like "M-Th"
        if '-' in day_range:
            start, end = day_range.split('-')
            
            # Map to full day names
            if start == 'M' and end == 'Th':
                for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday']:
                    schedule[day] = hours
            elif start == 'M' and end == 'F':
                for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                    schedule[day] = hours
        else:
            # Single day
            if day_range in day_map:
                schedule[day_map[day_range]] = hours
    
    return schedule


def save_to_csv(gym_data, filename='gym_hours.csv'):
    """Save gym hours data to CSV file"""
    
    if not gym_data:
        print("No data to save!")
        return
    
    print(f"\n{'='*80}")
    print(f"SAVING TO CSV")
    print(f"{'='*80}\n")
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['gym_name', 'campus', 'day', 'hours']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        # Remove schedule_type from each row when writing
        for row in gym_data:
            writer.writerow({
                'gym_name': row['gym_name'],
                'campus': row['campus'],
                'day': row['day'],
                'hours': row['hours']
            })
    
    print(f"✓ Successfully saved {len(gym_data)} records to {filename}")
    
    # Print summary
    print(f"\nSummary:")
    print(f"  - Total records: {len(gym_data)}")
    
    gyms = set(row['gym_name'] for row in gym_data)
    print(f"  - Gyms captured: {len(gyms)}")
    for gym in sorted(gyms):
        count = sum(1 for row in gym_data if row['gym_name'] == gym)
        print(f"    • {gym}: {count} days")


if __name__ == "__main__":
    soup = fetch_gym_hours()
    parsed_data = parse_gym_hours(soup)
    save_to_csv(parsed_data)
