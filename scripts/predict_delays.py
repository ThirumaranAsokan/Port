import os
import requests
import json
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd

# Supabase setup
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Hugging Face API setup
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-v0.1"

def get_pending_prediction_requests():
    """Get all vessels in the prediction queue with 'pending' status."""
    try:
        response = supabase.table("prediction_queue") \
            .select("*") \
            .eq("status", "pending") \
            .execute()
        
        return response.data
    except Exception as e:
        print(f"Error getting pending predictions: {e}")
        return []

def get_vessel_history(mmsi, vessel_name, hours=24):
    """Get historical position data for a specific vessel."""
    try:
        # Calculate time threshold
        time_threshold = (datetime.now(datetime.timezone.utc) - timedelta(hours=hours)).isoformat()
        
        # Query vessel positions
        response = supabase.table("vessel_positions") \
            .select("*") \
            .eq("mmsi", mmsi) \
            .gte("timestamp", time_threshold) \
            .order("timestamp", desc=False) \
            .execute()
        
        return response.data
    except Exception as e:
        print(f"Error getting vessel history for {vessel_name or mmsi}: {e}")
        return []

def format_data_for_prediction(vessel_data, history):
    """Prepare the data for the AI model to predict delays."""
    if not history:
        return None
    
    # Parse the position data if it's stored as a string
    if isinstance(vessel_data.get("position_data"), str):
        try:
            position_data = json.loads(vessel_data["position_data"])
        except:
            position_data = {}
    else:
        position_data = vessel_data.get("position_data", {})
    
    # Calculate average speed, course changes, etc.
    movement_data = analyze_movement_pattern(history)
    
    # Get historical traffic data if available
    traffic_data = get_traffic_data(position_data.get("lat"), position_data.get("lon"))
    
    # Format prompt for AI
    prompt = f"""
    Task: Predict vessel delay and provide rerouting suggestions based on the following data:
    
    Vessel: {vessel_data.get('vessel_name') or vessel_data.get('mmsi')}
    MMSI: {vessel_data.get('mmsi')}
    
    Current Position:
    Latitude: {position_data.get('lat')}
    Longitude: {position_data.get('lon')}
    Speed: {position_data.get('speed')} knots
    Course: {position_data.get('course')} degrees
    Timestamp: {position_data.get('timestamp')}
    
    Movement Analysis:
    Average Speed: {movement_data.get('avg_speed')} knots
    Speed Variation: {movement_data.get('speed_variation')}
    Course Changes: {movement_data.get('course_changes')}
    Stationary Periods: {movement_data.get('stationary_periods')}
    
    Traffic Information:
    Vessels in vicinity: {traffic_data.get('nearby_vessels')}
    Port congestion level: {traffic_data.get('congestion_level')}
    
    Based on this data:
    1. Is the vessel likely to be delayed? If so, by how many minutes?
    2. What is the confidence level of this prediction (express as a decimal between 0 and 1)?
    3. What are the potential causes of delay?
    4. Should the vessel consider rerouting? If so, provide a brief suggestion.
    
    Respond in JSON format with keys: delay_minutes, confidence, causes, rerouting_suggestion
    """
    
    return prompt

def analyze_movement_pattern(history):
    """Analyze vessel movement patterns to identify potential issues."""
    if not history:
        return {
            "avg_speed": "Unknown",
            "speed_variation": "Unknown",
            "course_changes": "Unknown",
            "stationary_periods": "Unknown"
        }
    
    try:
        # Convert to pandas DataFrame for analysis
        df = pd.DataFrame(history)
        
        # Calculate average speed
        avg_speed = df['speed'].mean() if 'speed' in df else "Unknown"
        
        # Calculate speed variation
        speed_variation = df['speed'].std() if 'speed' in df else "Unknown"
        
        # Count significant course changes (> 30 degrees)
        course_changes = 0
        if 'course' in df and len(df) > 1:
            for i in range(1, len(df)):
                diff = abs(df['course'].iloc[i] - df['course'].iloc[i-1])
                if diff > 30 and diff < 330:  # Handling the 0/360 boundary
                    course_changes += 1
        
        # Count stationary periods (speed < 1 knot)
        stationary_periods = 0
        if 'speed' in df:
            current_stationary = False
            for speed in df['speed']:
                if speed < 1.0 and not current_stationary:
                    stationary_periods += 1
                    current_stationary = True
                elif speed >= 1.0:
                    current_stationary = False
        
        return {
            "avg_speed": round(avg_speed, 2) if isinstance(avg_speed, (int, float)) else avg_speed,
            "speed_variation": round(speed_variation, 2) if isinstance(speed_variation, (int, float)) else speed_variation,
            "course_changes": course_changes,
            "stationary_periods": stationary_periods
        }
    
    except Exception as e:
        print(f"Error analyzing movement pattern: {e}")
        return {
            "avg_speed": "Error",
            "speed_variation": "Error",
            "course_changes": "Error",
            "stationary_periods": "Error"
        }

def get_traffic_data(lat, lon, radius_nm=20):
    """Get information about other vessels in the vicinity."""
    if not lat or not lon:
        return {
            "nearby_vessels": "Unknown",
            "congestion_level": "Unknown"
        }
    
    try:
        # Get current time
        now = datetime.now(datetime.timezone.utc)
        time_threshold = (now - timedelta(minutes=30)).isoformat()
        
        # Convert radius from nautical miles to approximate degrees
        # 1 nautical mile ≈ 0.01666 degrees at the equator
        radius_deg = radius_nm * 0.01666
        
        # Query for vessels in the area
        response = supabase.table("vessel_positions") \
            .select("mmsi", "vessel_name") \
            .gte("timestamp", time_threshold) \
            .lt("lat", lat + radius_deg) \
            .gt("lat", lat - radius_deg) \
            .lt("lon", lon + radius_deg) \
            .gt("lon", lon - radius_deg) \
            .execute()
        
        vessels = response.data
        
        # Count unique vessels
        unique_vessels = set()
        for vessel in vessels:
            unique_vessels.add(vessel.get("mmsi"))
        
        vessel_count = len(unique_vessels)
        
        # Determine congestion level
        if vessel_count < 5:
            congestion = "Low"
        elif vessel_count < 15:
            congestion = "Medium"
        else:
            congestion = "High"
        
        return {
            "nearby_vessels": vessel_count,
            "congestion_level": congestion
        }
    
    except Exception as e:
        print(f"Error getting traffic data: {e}")
        return {
            "nearby_vessels": "Error",
            "congestion_level": "Error"
        }

def query_huggingface(prompt):
    """Query the Hugging Face API for predictions."""
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
    
    try:
        response = requests.post(HF_API_URL, headers=headers, json=data)
        
        if response.status_code == 200:
            return response.json()[0]["generated_text"]
        else:
            print(f"Error querying Hugging Face API: {response.text}")
            return None
    except Exception as e:
        print(f"Exception in Hugging Face API call: {e}")
        return None

def extract_json_from_response(text):
    """Extract JSON from the LLM response."""
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

def save_prediction(vessel_data, prediction_data):
    """Save the prediction to the database."""
    try:
        # Extract values from prediction
        delay_minutes = prediction_data.get("delay_minutes", 0)
        if isinstance(delay_minutes, str):
            try:
                delay_minutes = int(delay_minutes)
            except:
                delay_minutes = 0
        
        confidence = prediction_data.get("confidence", 0.5)
        if isinstance(confidence, str):
            if confidence.lower() == "low":
                confidence = 0.3
            elif confidence.lower() == "medium":
                confidence = 0.6
            elif confidence.lower() == "high":
                confidence = 0.9
            else:
                try:
                    confidence = float(confidence)
                except:
                    confidence = 0.5
        
        reasoning = f"Causes: {prediction_data.get('causes', 'Unknown')}"
        if "rerouting_suggestion" in prediction_data:
            reasoning += f"\nRerouting: {prediction_data['rerouting_suggestion']}"
        
        # Save to Supabase
        result = supabase.table("delay_predictions").insert({
            "mmsi": vessel_data.get("mmsi"),
            "vessel_name": vessel_data.get("vessel_name"),
            "predicted_delay_minutes": delay_minutes,
            "confidence_score": confidence,
            "reasoning": reasoning,
            "created_at": datetime.now(datetime.timezone.utc).isoformat()
        }).execute()
        
        # Update prediction queue status
        supabase.table("prediction_queue") \
            .update({"status": "completed"}) \
            .eq("id", vessel_data.get("id")) \
            .execute()
        
        return result.data
    except Exception as e:
        print(f"Error saving prediction: {e}")
        return None

def main():
    """Main function to process pending predictions."""
    # Get pending prediction requests
    pending_predictions = get_pending_prediction_requests()
    
    if not pending_predictions:
        print("No pending predictions found.")
        return
    
    print(f"Found {len(pending_predictions)} pending predictions.")
    
    # Process each prediction request
    for vessel_data in pending_predictions:
        print(f"Processing prediction for vessel {vessel_data.get('vessel_name') or vessel_data.get('mmsi')}")
        
        # Get vessel history
        history = get_vessel_history(vessel_data.get("mmsi"), vessel_data.get("vessel_name"))
        
        # Format data for prediction
        prompt = format_data_for_prediction(vessel_data, history)
        if not prompt:
            print("Insufficient data for prediction, skipping.")
            continue
        
        # Query AI
        ai_response = query_huggingface(prompt)
        if not ai_response:
            print("Failed to get AI response, skipping.")
            continue
        
        # Extract JSON from response
        prediction_data = extract_json_from_response(ai_response)
        if not prediction_data:
            print("Failed to extract prediction data, skipping.")
            continue
        
        # Save prediction
        result = save_prediction(vessel_data, prediction_data)
        if result:
            print(f"Saved prediction for {vessel_data.get('vessel_name') or vessel_data.get('mmsi')}")
        else:
            print(f"Failed to save prediction for {vessel_data.get('vessel_name') or vessel_data.get('mmsi')}")

if __name__ == "__main__":
    main()
