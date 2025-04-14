import os
import glob
import requests
import pytesseract
import io
from PIL import Image
from supabase import create_client, Client
from pdf2image import convert_from_path, convert_from_bytes

# Supabase setup
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Hugging Face API setup
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-v0.1"

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF document."""
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path)
        
        # Extract text from each image
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img)
        
        return text
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_path}: {e}")
        return None

def extract_text_from_image(image_path):
    """Extract text from an image document."""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error extracting text from image {image_path}: {e}")
        return None

def document_already_processed(document_name):
    """Check if a document has already been processed."""
    try:
        response = supabase.table("brexit_documents") \
            .select("id") \
            .eq("document_name", document_name) \
            .execute()
        
        return len(response.data) > 0
    except Exception as e:
        print(f"Error checking if document exists: {e}")
        return False

def process_brexit_doc(document_name, document_type, text):
    """Process the document text with an AI model."""
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
    4. Any specific requirements for different ports or countries
    
    Format your response as JSON with the keys: "summary", "action_items", "deadlines", "port_requirements"
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
    
    try:
        response = requests.post(HF_API_URL, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()[0]["generated_text"]
            
            # Extract JSON
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = result[start_idx:end_idx]
                import json
                data = json.loads(json_str)
                return data
        else:
            print(f"Error in API response: {response.text}")
            
    except Exception as e:
        print(f"Error processing document with AI: {e}")
            
    return None

def save_document_analysis(document_name, document_type, analysis):
    """Save the document analysis to the database."""
    if not analysis:
        return None
    
    try:
        # Save to Supabase
        result = supabase.table("brexit_documents").insert({
            "document_name": document_name,
            "document_type": document_type,
            "summary": analysis.get("summary", ""),
            "action_items": analysis.get("action_items", ""),
            "deadlines": analysis.get("deadlines", ""),
            "port_requirements": analysis.get("port_requirements", ""),
            "created_at": datetime.now(datetime.timezone.utc).isoformat()
        }).execute()
        
        return result.data
    except Exception as e:
        print(f"Error saving document analysis: {e}")
        return None

def main():
    """Main function to process all new Brexit documents."""
    # Get all documents in the documents folder
    document_types = ["pdf", "jpg", "jpeg", "png", "txt"]
    all_documents = []
    
    for doc_type in document_types:
        all_documents.extend(glob.glob(f"documents/**/*.{doc_type}", recursive=True))
    
    if not all_documents:
        print("No documents found to process.")
        return
    
    print(f"Found {len(all_documents)} documents. Checking for new documents...")
    
    # Process each document
    for document_path in all_documents:
        document_name = os.path.basename(document_path)
        document_type = os.path.splitext(document_name)[1][1:].lower()
        
        # Check if document has already been processed
        if document_already_processed(document_name):
            print(f"Document {document_name} has already been processed, skipping.")
            continue
        
        print(f"Processing new document: {document_name}")
        
        # Extract text based on document type
        if document_type == 'pdf':
            text = extract_text_from_pdf(document_path)
        elif document_type in ['jpg', 'jpeg', 'png']:
            text = extract_text_from_image(document_path)
        else:
            # Assume plain text
            with open(document_path, 'r', encoding='utf-8') as f:
                text = f.read()
        
        if not text:
            print(f"Failed to extract text from {document_name}, skipping.")
            continue
        
        # Process with AI
        analysis = process_brexit_doc(document_name, document_type, text)
        
        # Save results
        if analysis:
            result = save_document_analysis(document_name, document_type, analysis)
            if result:
                print(f"Successfully processed and saved analysis for {document_name}")
            else:
                print(f"Failed to save analysis for {document_name}")
        else:
            print(f"Failed to get analysis for {document_name}")

if __name__ == "__main__":
    main()
