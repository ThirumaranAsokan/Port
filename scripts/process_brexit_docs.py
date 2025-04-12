import os
import requests
import pytesseract
import io
from PIL import Image
from supabase import create_client, Client
from pdf2image import convert_from_bytes

# Supabase setup
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Hugging Face API setup
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-v0.1"

def extract_text_from_pdf(pdf_bytes):
    try:
        # Convert PDF to images
        images = convert_from_bytes(pdf_bytes)
        
        # Extract text from each image
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img)
        
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

def extract_text_from_image(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return None

def process_brexit_doc(document_name, document_type, text):
    prompt = f"""
    Task: Analyze the following Brexit document text for port and shipping operations.
    
    Document: {document_name}
    Type: {document_type}
    
    Text:
    {text[:4000]}  # Limit text length to stay within context window
    
    Please provide:
    1. A concise summary of the document's key points (max 3 paragraphs)
    2. A list of specific action items that logistics managers, port authorities, or shipping companies need to take
    3. Any deadlines or important dates mentioned
    
    Format your response as JSON with the keys: "summary", "action_items", "deadlines"
    """
    
    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 1024,
            "temperature": 0.3
        }
    }
    
    response = requests.post(HF_API_URL, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()[0]["generated_text"]
        
        # Extract JSON
        try:
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = result[start_idx:end_idx]
                import json
                data = json.loads(json_str)
                return data
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            
    return None

def save_document_analysis(document_name, document_type, analysis):
    if not analysis:
        return None
    
    try:
        # Save to Supabase
        result = supabase.table("brexit_documents").insert({
            "document_name": document_name,
            "document_type": document_type,
            "summary": analysis.get("summary", ""),
            "action_items": analysis.get("action_items", "")
        }).execute()
        
        return result.data
    except Exception as e:
        print(f"Error saving document analysis: {e}")
        return None

def handle_new_document(document_name, document_type, file_bytes):
    # Extract text based on document type
    if document_type.lower().endswith('pdf'):
        text = extract_text_from_pdf(file_bytes)
    elif document_type.lower() in ['jpg', 'jpeg', 'png']:
        text = extract_text_from_image(file_bytes)
    else:
        # Assume plain text
        text = file_bytes.decode('utf-8')
    
    if not text:
        return None
    
    # Process with AI
    analysis = process_brexit_doc(document_name, document_type, text)
    
    # Save results
    if analysis:
        return save_document_analysis(document_name, document_type, analysis)
    
    return None
