import os
import requests
import json
from supabase import create_client, Client
from datetime import datetime, timedelta

# Supabase setup
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Hugging Face API setup
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-v0.1"

def fetch_recent_data():
    # Get the latest ABP data for each vessel
    abp_data = supabase.table("abp_vessel_data") \
        .select("*") \
        .order("created_at", desc=True) \
        .execute()
    
    # Get the latest AIS positions
    ais_data = supabase.table("ais_vessel_positions") \
        .select("*") \
        .order("created_at", desc=True) \
        .execute()
    
    return abp_data.data, ais_data.data

def format_data_for_prediction(abp_record, ais_records):
    # Find matching AIS records for this vessel
    matching_ais = [r for r in ais_records if r["vessel_name"] == abp_record["vessel_name"]]
    
    if not matching_ais:
        return None
    
    latest_ais = matching_ais[0]
    
    # Format prompt for AI
    prompt = f"""
    Task: Predict vessel delay and provide rerouting suggestions based on the data below.
    
    ABP Official Schedule:
    Vessel: {abp_record['vessel_name']}
    ETA: {abp_record['eta']}
    Berth: {abp_record['berth']}
    
    Current AIS Data:
    Vessel: {latest_ais['vessel_name']}
    Current Position: {latest_ais['lat']}, {latest_ais['lon']}
    Speed: {latest_ais.get('speed', 'N/A')} knots
    Course: {latest_ais.get('course', 'N/A')} degrees
    Last Update: {latest_ais['timestamp']}
    
    Based on this data:
    1. Is the vessel likely to be delayed? If so, by how many minutes?
    2. What is the confidence level of this prediction (low, medium, high)?
    3. What are the potential causes of delay?
    4. Should the vessel consider rerouting? If so, provide a brief suggestion.
    
    Respond in JSON format with keys: delay_minutes, confidence, causes, rerouting_suggestion
    """
    
    return prompt

def query_huggingface(prompt):
    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 512,
            "temperature": 0.7
        }
    }
    
    response = requests.post(HF_API_URL, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()[0]["generated_text"]
    else:
        print(f"Error querying Hugging Face API: {response.text}")
        return None

def extract_json_from_response(text):
    try:
        # Look for JSON pattern
        start_idx = text.find('{')
        end_idx = text.rfind('}') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = text[start_idx:end_idx]
            return json.loads(json_str)
        return None
    except Exception as e:
        print(f"Error extracting JSON: {e}")
        return None

def save_prediction(vessel_name, prediction_data):
    try:
        # Extract values from prediction
        delay_minutes = prediction_data.get("delay_minutes", 0)
        confidence = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.9
        }.get(prediction_data.get("confidence", "").lower(), 0.5)
        
        reasoning = f"Causes: {prediction_data.get('causes', 'Unknown')}"
        if "rerouting_suggestion" in prediction_data:
            reasoning += f"\nRerouting: {prediction_data['rerouting_suggestion']}"
        
        # Save to Supabase
        result = supabase.table("delay_predictions").insert({
            "vessel_name": vessel_name,
            "predicted_delay_minutes": int(delay_minutes) if isinstance(delay_minutes, (int, float, str)) else 0,
            "confidence_score": confidence,
            "reasoning": reasoning
        }).execute()
        
        return result.data
    except Exception as e:
        print(f"Error saving prediction: {e}")
        return None

def main():
    # Fetch recent data
    abp_data, ais_data = fetch_recent_data()
    
    # Process each vessel
    for abp_record in abp_data:
        # Skip if we already have a recent prediction for this vessel
        recent_predictions = supabase.table("delay_predictions") \
            .select("*") \
            .eq("vessel_name", abp_record["vessel_name"]) \
            .gte("created_at", (datetime.now() - timedelta(hours=1)).isoformat()) \
            .execute()
        
        if recent_predictions.data:
            continue
        
        # Format data for prediction
        prompt = format_data_for_prediction(abp_record, ais_data)
        if not prompt:
            continue
        
        # Query AI
        ai_response = query_huggingface(prompt)
        if not ai_response:
            continue
        
        # Extract JSON from response
        prediction_data = extract_json_from_response(ai_response)
        if not prediction_data:
            continue
        
        # Save prediction
        save_prediction(abp_record["vessel_name"], prediction_data)
        print(f"Saved prediction for {abp_record['vessel_name']}")

if __name__ == "__main__":
    main()
