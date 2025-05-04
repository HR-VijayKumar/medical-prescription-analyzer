import google.generativeai as genai
from pathlib import Path
import re
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from .env file
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found. Please check your .env file.")

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

# Model Configuration - keeping low temperature for accurate extraction
MODEL_CONFIG = {
    "temperature": 0.1,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 4096,
}

# Safety Settings
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
]

def load_image(image_path):
    """Load and format image for Gemini model."""
    img = Path(image_path)
    if not img.exists():
        raise FileNotFoundError(f"Could not find image: {img}")
    
    # Determine mime type from file extension or default to png
    extension = img.suffix.lstrip('.').lower()
    mime_map = {
        'jpg': 'jpeg',
        'jpeg': 'jpeg',
        'png': 'png',
        'webp': 'webp'
    }
    mime_type = mime_map.get(extension, 'png')
    
    return {
        "mime_type": f"image/{mime_type}",
        "data": img.read_bytes()
    }

def get_timing_text(timing_str):
    """
    Convert timing code like 1-0-1, 0-1/2-0 to text format.
    Returns a dictionary with dosing schedule.
    """
    if not timing_str:
        return {}
    
    parts = timing_str.split('-')
    if len(parts) != 3:
        return {}
    
    schedule = {}
    
    # Check each part of the timing string
    if parts[0] != "0" and parts[0] != "0/0":
        schedule["morning"] = parts[0]
    
    if parts[1] != "0" and parts[1] != "0/0":
        schedule["afternoon"] = parts[1]
    
    if parts[2] != "0" and parts[2] != "0/0":
        schedule["night"] = parts[2]
    
    return schedule

def clean_medicine_name(med_string):
    """
    Extract the clean medicine name by removing common prefixes/suffixes and dosage information.
    """
    # Common prefixes to remove
    prefixes = ["tab", "tabs", "tablet", "tablets", "cap", "caps", "capsule", "capsules", 
                "inj", "injection", "syp", "syrup", "susp", "suspension", "oint", "ointment",
                "cream", "lotion", "gel", "drop", "drops", "spray", "powder", "sachet", "t"]
    
    # Remove dosage pattern if it exists (e.g., "- 1-0-1")
    parts = med_string.lower().split('-', 1)
    med_info = parts[0].strip()
    
    # Remove common prefixes
    for prefix in prefixes:
        pattern = r"^" + prefix + r"\.?\s+"
        med_info = re.sub(pattern, "", med_info, flags=re.IGNORECASE)
    
    # Remove dosage strengths (numbers followed by mg, ml, etc.)
    med_info = re.sub(r'\b\d+\s*(?:mg|ml|mcg|g)\b', '', med_info, flags=re.IGNORECASE)
    
    # Remove standalone numbers
    med_info = re.sub(r'\b\d+\b', '', med_info)
    
    # Clean up any extra spaces
    med_info = re.sub(r'\s+', ' ', med_info).strip()
    
    return med_info

def clean_gemini_response(response_text):
    """
    Clean the Gemini response to extract just the JSON content.
    Removes markdown code blocks, JSON tags, etc.
    """
    # Remove markdown code blocks if present
    response_text = re.sub(r'```json\s*', '', response_text)
    response_text = re.sub(r'```\s*$', '', response_text)
    
    # Remove any leading/trailing whitespace
    response_text = response_text.strip()
    
    return response_text

def extract_prescription_information(image_path):
    """Extract comprehensive information from a prescription image."""
    
    # Initialize model
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        generation_config=MODEL_CONFIG,
        #safety_settings=SAFETY_SETTINGS
    )
    
    # Comprehensive system prompt to extract all required details
    system_prompt = """You are a specialist in analyzing medical prescriptions.
    Examine this prescription image carefully and extract the following information:
    
    1. PATIENT INFORMATION: Name, age, gender, any ID numbers, contact details, and vital information (like weight, height, blood pressure, etc.)
    
    2. DOCTOR INFORMATION: Name, qualifications, registration number, clinic/hospital name, contact information
    
    3. MEDICINES: For each medicine listed, extract:
       - Full medicine name including formulation (Tab, Cap, etc.) and strength
       - Dosage instructions (timing codes like 1-0-1, 1-1-1, 0-1/2-0)
       - Special instructions (if any, like "before food", "after food", etc.)
    
    Format your response as a structured JSON with these sections:
    
    {
      "patient_info": {
        "name": "",
        "age": "",
        "gender": "",
        "id": "",
        "contact": "",
        "vitals": {
          "weight": "",
          "height": "",
          "blood_pressure": "",
          "other": ""
        }
      },
      "doctor_info": {
        "name": "",
        "qualifications": "",
        "registration": "",
        "clinic": "",
        "contact": ""
      },
      "medicines": [
        {
          "full_name": "Tab. Metformin 500mg",
          "timing": "1-0-1",
          "special_instructions": "after food"
        }
      ]
    }
    
    Provide ONLY the JSON output without any markdown formatting or additional text.
    Be particularly careful with fractional doses like 1/2, 1/4, etc. Write them exactly as shown in the prescription.
    """
    
    # Load and process image
    image_info = load_image(image_path)
    
    try:
        # Generate response
        response = model.generate_content([system_prompt, image_info])
        
        # Clean the response text
        cleaned_response = clean_gemini_response(response.text)
        
        # Parse JSON response
        try:
            data = json.loads(cleaned_response)
            
            # Process medicines into the simplified format
            simplified_meds = {}
            
            for medicine in data.get("medicines", []):
                full_name = medicine.get("full_name", "")
                clean_name = clean_medicine_name(full_name)
                timing_str = medicine.get("timing", "")
                special_instr = medicine.get("special_instructions", "")
    
                schedule = get_timing_text(timing_str)
    
                if clean_name:
                    simplified_meds[clean_name] = {
                        "schedule": schedule,
                        "instructions": special_instr
                }
            
            # Create the final output structure
            result = {
                "patient_info": data.get("patient_info", {}),
                "doctor_info": data.get("doctor_info", {}),
                "medicines": simplified_meds
            }
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            print("Cleaned response:", cleaned_response)
            return {}
    
    except Exception as e:
        print(f"Error processing response: {e}")
        if 'response' in locals():
            print("Raw response:", response.text)
        return {}

def extract_medicine_names(image_path):
    """
    Process an image and extract just the medicine names as a list.
    This function is designed to be imported and used by other Python scripts.
    
    Args:
        image_path (str): Path to the prescription image
    
    Returns:
        list: List of extracted medicine names
    """
    prescription_data = extract_prescription_information(image_path)
    
    if prescription_data and "medicines" in prescription_data:
        # Return just the names of medicines as a list
        medicine_names = list(prescription_data["medicines"].keys())
        return medicine_names
    else:
        print("Failed to extract medicine names from prescription")
        return []

# Example usage when script is run directly
if __name__ == "__main__":
    # Define image path directly in the code
    image_path = r"Z:\Pictures\image5.jpg"  # MODIFY THIS PATH TO YOUR IMAGE
    
    print(f"Processing image: {image_path}")
    
    # Extract prescription information
    prescription_data = extract_prescription_information(image_path)
    
    if prescription_data:
        print("\nExtracted Prescription Data:")
        print(json.dumps(prescription_data, indent=2))
        
        # Extract just the medicine names
        medicine_names = extract_medicine_names(image_path)
        print("\nExtracted Medicine Names:")
        print(medicine_names)
    else:
        print("Failed to extract prescription data")