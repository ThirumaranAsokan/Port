import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
from supabase import create_client, Client  # Import Supabase library

def fetch_abp_data():
    URL = "https://www.southamptonvts.co.uk/Live-Information/Shipping-Movements/"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(URL, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching ABP data: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    if not table:
        print("Could not find table in ABP page")
        return None

    # Get headers
    ths = table.find("tr").find_all("th")
    col_names = [th.get_text(strip=True) for th in ths]

    # Get rows
    data = []
    for tr in table.find_all("tr")[1:]:
        cols = tr.find_all("td")
        if cols:
            row = [td.get_text(strip=True) for td in cols]
            data.append(row)

    # Create a DataFrame for better handling
    df = pd.DataFrame(data, columns=col_names)
    return df

def push_to_supabase(df: pd.DataFrame):
    """Pushes the DataFrame to Supabase."""

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print("SUPABASE_URL or SUPABASE_KEY environment variables not set.")
        return

    supabase: Client = create_client(supabase_url, supabase_key)

    for _, row in df.iterrows():
        data = row.to_dict()
        try:
            response = supabase.table("abp_vessel_data").insert(data).execute()
            if response.error:
                print(f"Error inserting row: {response.error}")
            else:
                print(f"Inserted row: {data}")
        except Exception as e:
            print(f"Error connecting to Supabase: {e}")

def main():
    df = fetch_abp_data()
    if df is not None:
        print(df.head())
        push_to_supabase(df)  # Push data to Supabase
    else:
        print("No data fetched.")

if __name__ == "__main__":
    main()
