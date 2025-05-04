import gradio as gr
import uuid
from pdf_generator import generate_prescription_pdf
from prescription_data import extract_prescription_information, extract_medicine_names
from medicine_info import process_medicine_list
from io import BytesIO
import tempfile
import os

# Define application title and disclaimer
APP_TITLE = "Medical Prescription Analyzer"
DISCLAIMER = """
**Disclaimer:** This tool is for informational purposes only and not a substitute for professional medical advice. 
The analysis may not be 100% accurate. Always consult with a healthcare professional before making any decisions 
based on this information.
"""

HOW_TO_USE = """
### How to Use:
1. Upload your prescription image using the upload area on the left
2. Click the "Analyze Prescription" button to process the image
3. View the analysis results below
4. Download the detailed PDF report if needed
5. Use the "Clear & Restart" button to analyze another prescription
"""

# Processing function using temporary files instead of permanent storage
def process_prescription(image):
    if image is None:
        return "### ⚠️ Please upload a prescription image first.", None
    
    try:
        # Create a temporary file for processing instead of saving to disk permanently
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_path = temp_file.name
            image.save(temp_path)
        
        try:
            # Extract prescription data
            prescription_data = extract_prescription_information(temp_path)
            
            if not prescription_data or not prescription_data.get("medicines"):
                return "### ⚠️ Error: Failed to extract prescription data. Please try with a clearer image.", None
            
            medicine_names = extract_medicine_names(temp_path)
            medicine_information = process_medicine_list(medicine_names)

            # Correct the medicine names
            corrected_names = [name.capitalize() for name in medicine_information]

            # Generate PDF using the prescription data and medicine info
            pdf_path = generate_prescription_pdf(prescription_data, medicine_information)

            # Prepare the summary for display
            patient = prescription_data.get("patient_info", {})
            doctor = prescription_data.get("doctor_info", {})

            summary_lines = [
                "### ✅ Analysis Complete\n",
                f"**Patient Name:** {patient.get('name', 'N/A')}",
                f"**Age:** {patient.get('age', 'N/A')}",
                f"**Gender:** {patient.get('gender', 'N/A')}",
                f"**Doctor Name:** {doctor.get('name', 'N/A')}",
                "\n**Medicines Extracted:**"
            ]
            for idx, name in enumerate(corrected_names, 1):
                summary_lines.append(f"{idx}. {name}")

            summary = "\n".join(summary_lines)
            
            return summary, pdf_path
        
        finally:
            # Clean up the temporary file regardless of success or failure
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except Exception as e:
        return f"### ⚠️ Error: {str(e)}\nPlease try again or use a different image.", None

def clear_interface():
    return None, "### Results will appear here after analysis", None

# Custom CSS for better layout
custom_css = """
#image_upload {
    min-height: 300px;
}
"""

# Gradio interface setup with custom CSS
with gr.Blocks(theme=gr.themes.Soft(), css=custom_css) as demo:
    # App title and disclaimer at the top
    gr.Markdown(f"# {APP_TITLE}")
    gr.Markdown(DISCLAIMER)
    
    # How to use section on the top left
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown(HOW_TO_USE)
            
            # Upload image (left side)
            image_input = gr.Image(
                type="pil", 
                label="Upload Prescription Image", 
                sources=["upload"],
                elem_id="image_upload"
            )
            
        with gr.Column(scale=1):
            # Analysis buttons on top right
            with gr.Row():
                submit_btn = gr.Button("Analyze Prescription", variant="primary", size="lg")
                clear_btn = gr.Button("Clear & Restart", variant="secondary", size="lg")
                
            # Analysis results below the buttons
            output_text = gr.Markdown("### Results will appear here after analysis")
            
            # Download section at the bottom
            download_btn = gr.File(label="Download Detailed Report (PDF)", interactive=False)

    # Linking the functions to the buttons
    submit_btn.click(
        fn=process_prescription, 
        inputs=[image_input], 
        outputs=[output_text, download_btn]
    )
    
    clear_btn.click(
        fn=clear_interface,
        inputs=[],
        outputs=[image_input, output_text, download_btn]
    )

# Launch the app
if __name__ == "__main__":
    demo.launch()