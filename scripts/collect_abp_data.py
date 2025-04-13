import requests
from bs4 import BeautifulSoup
import pandas as pd
from supabase import create_client, Client
import os
from datetime import datetime
import time
import re

# --- Supabase Setup ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# This is for Southampton port. Modify for other ABP ports as needed.
ABP_BASE_URL = "https://www.southamptonvts.co.uk/Live_Information/Shipping_Movements_and_Cruise_Ship_Schedule/"
ABP_VESSELS_ALONGSIDE_URL = ABP_BASE_URL + "Vessels_Alongside/"
ABP_PLANNED_MOVEMENTS_URL = ABP_BASE_URL + "Planned_Movements/"
ABP_VESSELS_UNDERWAY_URL = ABP_BASE_URL + "Vessels_Underway/"
ABP_SHIPS_AT_ANCHOR_URL = ABP_BASE_URL + "Ships_at_Anchor/"

def fetch_page(url):
    """Fetch a webpage with retry logic"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Attempting to fetch {url}")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            content = response.content
            
            # Debug - show a sample of the content
            try:
                content_sample = content[:200].decode('utf-8', errors='replace')
                print(f"Sample content from {url}: {content_sample}")
            except Exception as e:
                print(f"Could not decode content sample: {e}")
            
            # Debug - check for tables
            soup = BeautifulSoup(content, 'html.parser')
            tables = soup.find_all('table')
            print(f"Found {len(tables)} tables in the response")
            
            # Check for other potential data containers
            divs = soup.find_all('div', class_=['data', 'container', 'content', 'table', 'vessels'])
            print(f"Found {len(divs)} potential data divs in the response")
            
            # Try to find vessel information by looking for common pattern
            vessel_elements = soup.find_all(text=re.compile(r'vessel|ship|name|berth|eta', re.IGNORECASE))
            if vessel_elements:
                print(f"Found {len(vessel_elements)} elements containing vessel-related text")
            
            return content
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retrying
    
    print(f"Failed to fetch {url} after {max_retries} attempts")
    return None

def parse_date_time(date_str, time_str=None):
    """Parse date and time strings into ISO format"""
    try:
        # Clean up inputs
        if date_str:
            date_str = date_str.strip()
        if time_str:
            time_str = time_str.strip()
        else:
            # If no separate time string, try to extract from date_str
            match = re.search(r'(\d{1,2}[-\s][A-Za-z]{3})\s*(\d{1,2}:\d{1,2})', date_str)
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
        
        # If we still don't have time_str
        if not time_str:
            return None
            
        # Get current year
        current_year = datetime.now().year
        
        # Try various date formats
        date_formats = [
            f"{date_str} {time_str} {current_year}",
            f"{date_str} {time_str}",
        ]
        
        format_strings = [
            '%d-%b %H:%M %Y',
            '%d %b %H:%M %Y',
            '%d-%b %H:%M',
            '%d %b %H:%M',
        ]
        
        for date_format in date_formats:
            for format_string in format_strings:
                try:
                    dt = datetime.strptime(date_format, format_string)
                    # Add year if not in format string
                    if '%Y' not in format_string:
                        dt = dt.replace(year=current_year)
                    return dt.isoformat()
                except ValueError:
                    continue
        
        print(f"Could not parse date/time: {date_str} {time_str}")
        return None
    except Exception as e:
        print(f"Error parsing date/time: {e}")
        return None

def extract_table_data(html_content, status):
    """Extract vessel data from HTML content"""
    if not html_content:
        print(f"No HTML content for {status} data")
        return []
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # First try to find tables
        tables = soup.find_all('table')
        
        if not tables:
            print(f"No tables found for {status} data")
            
            # Try alternative approach: look for div containers that might contain vessel data
            data_containers = soup.find_all(['div', 'section'], class_=lambda c: c and any(term in c.lower() for term in ['data', 'container', 'content', 'vessels', 'table']))
            if data_containers:
                print(f"Found {len(data_containers)} potential data containers")
                
                # Try to extract vessel data from these containers
                vessels_data = []
                
                for container in data_containers:
                    # Look for vessel names
                    vessel_elements = container.find_all(text=re.compile(r'vessel|ship|name', re.IGNORECASE))
                    if vessel_elements:
                        print(f"Found {len(vessel_elements)} vessel name candidates in container")
                        
                        # This is just a basic implementation - would need to adapt based on actual HTML structure
                        for elem in vessel_elements:
                            vessel_name = elem.strip()
                            if vessel_name and len(vessel_name) > 3:  # Basic validation
                                vessels_data.append({
                                    "vessel_name": vessel_name,
                                    "eta": None,  # Would need to find related ETA
                                    "berth": None,  # Would need to find related berth
                                    "status": status
                                })
                
                if vessels_data:
                    print(f"Extracted {len(vessels_data)} vessels using alternative approach")
                    return vessels_data
            
            return []
        
        # Try to find the right table (usually the largest one)
        main_table = None
        max_rows = 0
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > max_rows:
                max_rows = len(rows)
                main_table = table
        
        if not main_table:
            print(f"Could not identify main table for {status} data")
            return []
        
        # Extract header row to determine column indices
        header_row = main_table.find('tr')
        if not header_row:
            print(f"No header row found for {status} data")
            return []
        
        # Debug - print header row content
        header_cells = header_row.find_all(['th', 'td'])
        print(f"Header row has {len(header_cells)} cells with content: {[cell.text.strip() for cell in header_cells]}")
        
        headers = [th.text.strip().lower() for th in header_cells]
        
        # Find relevant column indices
        vessel_idx = next((i for i, h in enumerate(headers) if 'vessel' in h or 'ship' in h or 'name' in h), None)
        eta_idx = next((i for i, h in enumerate(headers) if 'eta' in h or 'arrival' in h or 'time' in h), None)
        berth_idx = next((i for i, h in enumerate(headers) if 'berth' in h or 'location' in h), None)
        
        # Debug - print column indices
        print(f"Column indices - Vessel: {vessel_idx}, ETA: {eta_idx}, Berth: {berth_idx}")
        
        # If we couldn't find vessel column, default to first column
        if vessel_idx is None:
            print("Could not identify vessel column, defaulting to first column")
            vessel_idx = 0
        
        # Extract data rows
        data_rows = main_table.find_all('tr')[1:]  # Skip header
        vessels_data = []
        
        print(f"Found {len(data_rows)} data rows in the table")
        
        for row in data_rows:
            cells = row.find_all('td')
            if not cells:
                continue
                
            # Debug - print row content
            print(f"Row has {len(cells)} cells")
            
            if len(cells) <= vessel_idx:
                print(f"Row doesn't have enough cells (only {len(cells)}, need {vessel_idx+1})")
                continue
            
            # Extract vessel name
            vessel_name = cells[vessel_idx].text.strip()
            if not vessel_name:
                print("Empty vessel name, skipping row")
                continue
            
            print(f"Found vessel: {vessel_name}")
            
            # Extract ETA if available
            eta = None
            if eta_idx is not None and len(cells) > eta_idx:
                eta_text = cells[eta_idx].text.strip()
                if eta_text:
                    print(f"ETA text: {eta_text}")
                    # Handle different formats of ETA data
                    eta_parts = eta_text.split('\n')
                    if len(eta_parts) >= 2:
                        eta = parse_date_time(eta_parts[0], eta_parts[1])
                    else:
                        eta = parse_date_time(eta_text)
                    print(f"Parsed ETA: {eta}")
            
            # Extract berth if available
            berth = None
            if berth_idx is not None and len(cells) > berth_idx:
                berth = cells[berth_idx].text.strip()
                print(f"Berth: {berth}")
            
            vessels_data.append({
                "vessel_name": vessel_name,
                "eta": eta,
                "berth": berth,
                "status": status
            })
        
        print(f"Found {len(vessels_data)} vessels with {status} status")
        return vessels_data
        
    except Exception as e:
        print(f"Error parsing HTML for {status} data: {e}")
        return []

def store_abp_data(data):
    """Store processed ABP data in Supabase"""
    if not data:
        print("No ABP data to store.")
        return
    
    success_count = 0
    error_count = 0
    
    for item in data:
        try:
            insert_data = {
                "vessel_name": item.get("vessel_name"),
                "eta": item.get("eta"),
                "berth": item.get("berth"),
                "status": item.get("status"),
                "created_at": datetime.now().isoformat()
            }
            
            response = supabase.table("abp_vessel_data").insert(insert_data).execute()
            
            if response.data:
                success_count += 1
            else:
                error_count += 1
                print(f"Failed to insert data for: {item.get('vessel_name')}")
        
        except Exception as e:
            error_count += 1
            print(f"Error inserting data for {item.get('vessel_name')}: {e}")
    
    print(f"Successfully stored {success_count} records, {error_count} failed")

def check_website_structure(url):
    """Check the website structure to determine how to extract data"""
    try:
        print(f"Checking website structure for {url}")
        content = fetch_page(url)
        
        if not content:
            return
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for common data structures
        print("\nAnalyzing page structure:")
        
        # Check for tables
        tables = soup.find_all('table')
        print(f"- Found {len(tables)} tables")
        
        # Check for data in divs with specific classes
        data_divs = soup.find_all('div', class_=lambda c: c and any(term in str(c).lower() for term in ['data', 'vessel', 'ship', 'table']))
        print(f"- Found {len(data_divs)} div elements that might contain data")
        
        # Check for JavaScript data
        scripts = soup.find_all('script')
        js_data_scripts = [s for s in scripts if s.string and any(term in s.string.lower() for term in ['vessel', 'ship', 'data', 'json'])]
        print(f"- Found {len(js_data_scripts)} script elements that might contain vessel data")
        
        # Look for iframe embedding
        iframes = soup.find_all('iframe')
        print(f"- Found {len(iframes)} iframes that might embed content")
        
        # Try to find any mention of vessels or ships
        vessel_mentions = soup.find_all(text=re.compile(r'vessel|ship|cruise|arrival|departure', re.IGNORECASE))
        print(f"- Found {len(vessel_mentions)} mentions of vessel-related terms")
        
        # Print the first few examples of vessel mentions
        if vessel_mentions:
            print("\nSample vessel-related content:")
            for i, mention in enumerate(vessel_mentions[:5]):
                parent = mention.parent
                print(f"  {i+1}. '{mention.strip()}' in a {parent.name} element")
        
        print("\nSuggested approach based on analysis:")
        if tables:
            print("- Use table extraction (original approach)")
        elif js_data_scripts:
            print("- Extract data from JavaScript/JSON")
        elif data_divs:
            print("- Extract from structured div elements")
        elif iframes:
            print("- Follow iframe sources for data")
        else:
            print("- Site structure has changed significantly, manual review needed")
            
    except Exception as e:
        print(f"Error analyzing website structure: {e}")

def main():
    """Main function to collect ABP vessel data"""
    print("Starting ABP data collection...")
    
    # First, check the website structure
    print("\n=== Analyzing website structure ===")
    check_website_structure(ABP_VESSELS_ALONGSIDE_URL)
    
    # Initialize total vessel count
    total_vessels = 0
    all_vessels = []
    
    try:
        # Collect data for vessels alongside
        print("\n=== Collecting vessels alongside data ===")
        alongside_html = fetch_page(ABP_VESSELS_ALONGSIDE_URL)
        if alongside_html:
            alongside_vessels = extract_table_data(alongside_html, "Alongside")
            all_vessels.extend(alongside_vessels)
            total_vessels += len(alongside_vessels)
        else:
            print("No data fetched for vessels alongside.")
        
        # Collect data for planned movements
        print("\n=== Collecting planned movements data ===")
        planned_html = fetch_page(ABP_PLANNED_MOVEMENTS_URL)
        if planned_html:
            planned_vessels = extract_table_data(planned_html, "Planned")
            all_vessels.extend(planned_vessels)
            total_vessels += len(planned_vessels)
        else:
            print("No data fetched for planned movements.")
        
        # Collect data for vessels underway
        print("\n=== Collecting vessels underway data ===")
        underway_html = fetch_page(ABP_VESSELS_UNDERWAY_URL)
        if underway_html:
            underway_vessels = extract_table_data(underway_html, "Underway")
            all_vessels.extend(underway_vessels)
            total_vessels += len(underway_vessels)
        else:
            print("No data fetched for vessels underway.")
        
        # Collect data for ships at anchor
        print("\n=== Collecting ships at anchor data ===")
        anchor_html = fetch_page(ABP_SHIPS_AT_ANCHOR_URL)
        if anchor_html:
            anchor_vessels = extract_table_data(anchor_html, "At Anchor")
            all_vessels.extend(anchor_vessels)
            total_vessels += len(anchor_vessels)
        else:
            print("No data fetched for ships at anchor.")
        
        # Check if we got any data
        if total_vessels == 0:
            print("\nNo vessel data was collected from any source.")
            print("The website structure may have changed. Manual review is recommended.")
            return
        
        # Store data
        print(f"\nStoring {total_vessels} vessel records...")
        store_abp_data(all_vessels)
        
        print("\nABP data collection complete")
        
    except Exception as e:
        print(f"\nError in main function: {e}")

if __name__ == "__main__":
    main()
