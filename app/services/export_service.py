"""
Export Service - Handles PDF export and JSON backup/restore operations.
"""

import json
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from app.i18n.translations import TranslationService
from app.services.calculation_service import CalculationService


# Register Noto Sans fonts for multilingual support (Turkish, English, Korean)
# Font files located in app/fonts/ directory
try:
    fonts_dir = os.path.join(os.path.dirname(__file__), '..', 'fonts')
    
    regular_font_path = os.path.join(fonts_dir, 'NotoSans-Regular.ttf')
    bold_font_path = os.path.join(fonts_dir, 'NotoSans-Bold.ttf')
    
    if os.path.exists(regular_font_path):
        pdfmetrics.registerFont(TTFont('NotoSans', regular_font_path))
    
    if os.path.exists(bold_font_path):
        pdfmetrics.registerFont(TTFont('NotoSans-Bold', bold_font_path))
    
    _DEFAULT_FONT = 'NotoSans'
    _DEFAULT_FONT_BOLD = 'NotoSans-Bold'
    
except Exception as e:
    # Fallback to Helvetica if fonts not found
    print(f"Warning: Could not load Noto Sans fonts: {e}")
    _DEFAULT_FONT = 'Helvetica'
    _DEFAULT_FONT_BOLD = 'Helvetica-Bold'


class ExportService:
    """Handles data export (PDF) and backup (JSON) operations."""
    
    @staticmethod
    def export_clients_to_pdf(clients_data, output_path):
        """
        Export clients list to PDF.
        
        Args:
            clients_data: List of client dictionaries
            output_path: File path where PDF will be saved
            
        Returns:
            Tuple: (success: bool, message: str)
        """
        try:
            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch
            )
            
            # Container for PDF elements
            elements = []
            
            # Get translation based on current language
            title = TranslationService.get("clients.title", "Clients")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # Add title
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                fontName=_DEFAULT_FONT_BOLD,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=12,
                alignment=1  # Center alignment
            )
            
            title_text = f"{title} - {TranslationService.get('common.export', 'Export')} {timestamp}"
            elements.append(Paragraph(title_text, title_style))
            elements.append(Spacer(1, 0.3*inch))
            
            # Prepare table data
            if not clients_data:
                elements.append(Paragraph(
                    TranslationService.get("clients.no_clients", "No clients found"),
                    styles['Normal']
                ))
            else:
                # Table headers
                headers = [
                    TranslationService.get("clients.full_name", "Full Name"),
                    TranslationService.get("clients.email", "Email"),
                    TranslationService.get("clients.phone", "Phone"),
                    TranslationService.get("clients.age", "Age"),
                    TranslationService.get("clients.gender", "Gender")
                ]
                
                # Build table rows
                table_data = [headers]
                for client in clients_data:
                    # Calculate age from birth_date
                    birth_date = client.get('birth_date', '')
                    age_str = ''
                    if birth_date:
                        age = CalculationService.calculate_age(birth_date)
                        age_str = str(age) if age is not None else ''
                    
                    # Translate gender value
                    gender = client.get('gender', '')
                    if gender.lower() == 'male':
                        gender_translated = TranslationService.get("clients.male", "Male")
                    elif gender.lower() == 'female':
                        gender_translated = TranslationService.get("clients.female", "Female")
                    elif gender.lower() == 'other':
                        gender_translated = TranslationService.get("clients.other", "Other")
                    else:
                        gender_translated = gender
                    
                    row = [
                        client.get('full_name', ''),
                        client.get('email', ''),
                        client.get('phone', ''),
                        age_str,
                        gender_translated
                    ]
                    table_data.append(row)
                
                # Create table with Noto Sans styling
                table = Table(table_data, colWidths=[1.8*inch, 1.8*inch, 1.2*inch, 0.7*inch, 0.8*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), _DEFAULT_FONT_BOLD),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('FONTNAME', (0, 1), (-1, -1), _DEFAULT_FONT),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
                ]))
                
                elements.append(table)
            
            # Build PDF
            doc.build(elements)
            return True, TranslationService.get("messages.export_success", "PDF exported successfully!")
            
        except Exception as e:
            error_msg = TranslationService.get("messages.export_error", "Error exporting PDF: ") + str(e)
            return False, error_msg
    
    @staticmethod
    def backup_to_json(db, output_path):
        """
        Backup all data (clients, diets, measurements) to JSON.
        
        Args:
            db: MongoDB database connection
            output_path: File path where JSON backup will be saved
            
        Returns:
            Tuple: (success: bool, message: str)
        """
        try:
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "backup_version": "1.0",
                "collections": {}
            }
            
            # Backup clients collection
            if 'clients' in db.list_collection_names():
                clients = list(db['clients'].find())
                backup_data['collections']['clients'] = [
                    {**doc, '_id': str(doc['_id'])} for doc in clients
                ]
            
            # Backup diet plans collection
            if 'diet_plans' in db.list_collection_names():
                diets = list(db['diet_plans'].find())
                backup_data['collections']['diet_plans'] = [
                    {**doc, '_id': str(doc['_id']), 'client_id': str(doc.get('client_id', ''))} 
                    for doc in diets
                ]
            
            # Backup measurements collection
            if 'measurements' in db.list_collection_names():
                measurements = list(db['measurements'].find())
                backup_data['collections']['measurements'] = [
                    {**doc, '_id': str(doc['_id']), 'client_id': str(doc.get('client_id', ''))} 
                    for doc in measurements
                ]
            
            # Write to JSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
            
            return True, TranslationService.get("messages.backup_success", "Backup created successfully!")
            
        except Exception as e:
            error_msg = TranslationService.get("messages.backup_error", "Error creating backup: ") + str(e)
            return False, error_msg
    
    @staticmethod
    def restore_from_json(db, input_path):
        """
        Restore data from JSON backup.
        WARNING: This will overwrite existing data!
        
        Args:
            db: MongoDB database connection
            input_path: Path to JSON backup file
            
        Returns:
            Tuple: (success: bool, message: str)
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            collections = backup_data.get('collections', {})
            
            # Restore each collection
            restored_count = 0
            for collection_name, documents in collections.items():
                if documents and collection_name in db.list_collection_names():
                    # Clear existing data
                    db[collection_name].delete_many({})
                    
                    # Convert string IDs back to ObjectId if needed
                    from bson.objectid import ObjectId
                    for doc in documents:
                        if '_id' in doc:
                            try:
                                doc['_id'] = ObjectId(doc['_id'])
                            except:
                                pass
                        
                        # Convert client_id strings back to ObjectId
                        if 'client_id' in doc and isinstance(doc['client_id'], str):
                            try:
                                doc['client_id'] = ObjectId(doc['client_id'])
                            except:
                                pass
                    
                    # Insert documents
                    result = db[collection_name].insert_many(documents)
                    restored_count += len(result.inserted_ids)
            
            success_msg = TranslationService.get("messages.restore_success", f"Backup restored successfully! ({restored_count} records)")
            return True, success_msg
            
        except FileNotFoundError:
            error_msg = TranslationService.get("messages.file_not_found", "Backup file not found!")
            return False, error_msg
        except json.JSONDecodeError:
            error_msg = TranslationService.get("messages.invalid_backup_file", "Invalid backup file format!")
            return False, error_msg
        except Exception as e:
            error_msg = TranslationService.get("messages.restore_error", "Error restoring backup: ") + str(e)
            return False, error_msg
