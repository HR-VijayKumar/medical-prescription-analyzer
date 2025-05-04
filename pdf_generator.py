from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
)
from io import BytesIO
import tempfile

def generate_prescription_pdf(prescriptions, medicine_details):
    # Generate filename based on timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Prescription_{timestamp}.pdf"
    
    # Create a temporary file for the PDF
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    file_path = temp_pdf.name
    
    # PDF setup
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    styles = getSampleStyleSheet()
    custom_style = ParagraphStyle(name='Custom', fontSize=10, leading=14)

    elements = []

    # Title
    elements.append(Paragraph("Prescription Report", styles['Title']))
    elements.append(Spacer(1, 12))

    # Patient Info
    elements.append(Paragraph("Patient Information", styles['Heading2']))
    patient = prescriptions.get('patient_info', {})
    vitals = patient.get('vitals', {})
    elements.extend([
        Paragraph(f"<b>Name:</b> {patient.get('name', 'N/A')}", custom_style),
        Paragraph(f"<b>Age:</b> {patient.get('age', 'N/A')}", custom_style),
        Paragraph(f"<b>Gender:</b> {patient.get('gender', 'N/A')}", custom_style),
        Paragraph(f"<b>ID:</b> {patient.get('id', 'N/A')}", custom_style),
        Paragraph(f"<b>Contact:</b> {patient.get('contact', 'N/A')}", custom_style),
        Paragraph(f"<b>Vitals:</b>", custom_style),
        Paragraph(f" - Weight: {vitals.get('weight', 'N/A')}", custom_style),
        Paragraph(f" - Height: {vitals.get('height', 'N/A')}", custom_style),
        Paragraph(f" - Blood Pressure: {vitals.get('blood_pressure', 'N/A')}", custom_style),
        Paragraph(f" - Other: {vitals.get('other', 'N/A')}", custom_style),
        Spacer(1, 12)
    ])

    # Doctor Info
    elements.append(Paragraph("Doctor Information", styles['Heading2']))
    doc_info = prescriptions.get('doctor_info', {})
    elements.extend([
        Paragraph(f"<b>Name:</b> {doc_info.get('name', 'N/A')}", custom_style),
        Paragraph(f"<b>Qualifications:</b> {doc_info.get('qualifications', 'N/A')}", custom_style),
        Paragraph(f"<b>Registration No:</b> {doc_info.get('registration', 'N/A')}", custom_style),
        Paragraph(f"<b>Clinic:</b> {doc_info.get('clinic', 'N/A')}", custom_style),
        Paragraph(f"<b>Contact:</b> {doc_info.get('contact', 'N/A')}", custom_style),
        Spacer(1, 12)
    ])

    # Medicine Schedules Table with Morning, Afternoon, Night
    elements.append(Paragraph("Medicine Schedule", styles['Heading2']))
    table_data = [['Medicine', 'Morning', 'Afternoon', 'Night']]
    for med, info in prescriptions.get('medicines', {}).items():
        schedule = info.get('schedule', {})
        table_data.append([
            med.title(),
            schedule.get('morning', '-'),
            schedule.get('afternoon', '-'),
            schedule.get('night', '-')
        ])
    t = Table(table_data, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    # Medicine Details
    for name, details in medicine_details.items():
        elements.append(Paragraph(f"Medicine: {name}", styles['Heading3']))
        for key, val in details.items():
            if key != 'url':
                elements.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b>", custom_style))
                
                # Handle different data types
                if isinstance(val, str):
                    lines = [line.strip() for line in val.splitlines() if line.strip()]
                elif isinstance(val, list):
                    lines = [str(item).strip() for item in val if str(item).strip()]
                else:
                    lines = [str(val).strip()]

                bullets = ListFlowable(
                    [ListItem(Paragraph(line, custom_style)) for line in lines],
                    bulletType='bullet'
                )
                elements.append(bullets)
            else:
                elements.append(Paragraph(f"<b>More Info:</b> <a href='{val}'>{val}</a>", custom_style))
        elements.append(Spacer(1, 12))

    # Build PDF
    doc.build(elements)
    
    return file_path