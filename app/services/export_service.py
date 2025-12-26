"""
Export Service - Handles PDF export and JSON backup/restore operations.
"""

import json
import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

from app.i18n.translations import TranslationService
from app.services.calculation_service import CalculationService


def _safe_register_family(family_name: str, regular_path: str, bold_path: str):
    pdfmetrics.registerFont(TTFont(family_name, regular_path))
    pdfmetrics.registerFont(TTFont(f"{family_name}-Bold", bold_path))
    registerFontFamily(
        family_name,
        normal=family_name,
        bold=f"{family_name}-Bold",
        italic=family_name,
        boldItalic=f"{family_name}-Bold",
    )


def _register_fonts():
    """
    Registers 2 font families:
      - AppLatin (DejaVu Sans) for TR/EN
      - AppKR (NotoSansKR) for KO
    """
    fonts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fonts"))

    dv_regular = os.path.join(fonts_dir, "DejaVuSans.ttf")
    dv_bold = os.path.join(fonts_dir, "DejaVuSans-Bold.ttf")

    kr_regular = os.path.join(fonts_dir, "NotoSansKR-Regular.ttf")
    kr_bold = os.path.join(fonts_dir, "NotoSansKR-Bold.ttf")

    ok = {"latin": False, "kr": False}

    try:
        if os.path.exists(dv_regular) and os.path.exists(dv_bold):
            _safe_register_family("AppLatin", dv_regular, dv_bold)
            ok["latin"] = True
        else:
            print("⚠ Missing DejaVu fonts (TR/EN): DejaVuSans.ttf, DejaVuSans-Bold.ttf")

        if os.path.exists(kr_regular) and os.path.exists(kr_bold):
            _safe_register_family("AppKR", kr_regular, kr_bold)
            ok["kr"] = True
        else:
            print("⚠ Missing NotoSansKR fonts (KO): NotoSansKR-Regular.ttf, NotoSansKR-Bold.ttf")

    except Exception as e:
        print(f"⚠ Font registration error: {e}")

    print(f"✓ Font status: {ok}")
    return ok


_FONT_OK = _register_fonts()


def _pick_fonts_by_language():
    """
    Choose the correct font based on TranslationService language:
      - ko -> AppKR
      - otherwise -> AppLatin
    """
    lang = (TranslationService.get_current_language() or "en").lower()

    if lang == "ko" and _FONT_OK.get("kr"):
        return "AppKR", "AppKR-Bold"

    if _FONT_OK.get("latin"):
        return "AppLatin", "AppLatin-Bold"

    return "Helvetica", "Helvetica-Bold"


class ExportService:
    """Handles data export (PDF) and backup (JSON) operations."""

    @staticmethod
    def export_clients_to_pdf(clients_data, output_path):
        """
        Export clients list to PDF.
        Returns: (success: bool, message: str)
        """
        try:
            font_normal, font_bold = _pick_fonts_by_language()

            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=0.5 * inch,
                leftMargin=0.5 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch,
            )

            elements = []
            styles = getSampleStyleSheet()

            normal_style = ParagraphStyle(
                "CustomNormal",
                parent=styles["Normal"],
                fontName=font_normal,
                fontSize=10,
                textColor=colors.black,
            )

            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontName=font_bold,
                fontSize=18,
                textColor=colors.HexColor("#2c3e50"),
                spaceAfter=12,
                alignment=1,
            )

            title = TranslationService.get("clients.title", "Clients")
            export_label = TranslationService.get("buttons.export", "Export")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

            title_text = f"{title} - {export_label} {timestamp}"
            elements.append(Paragraph(title_text, title_style))
            elements.append(Spacer(1, 0.3 * inch))

            if not clients_data:
                elements.append(
                    Paragraph(
                        TranslationService.get("clients.no_clients", "No clients found"),
                        normal_style,
                    )
                )
            else:
                headers = [
                    TranslationService.get("clients.full_name", "Full Name"),
                    TranslationService.get("clients.email", "Email"),
                    TranslationService.get("clients.phone", "Phone"),
                    TranslationService.get("clients.age", "Age"),
                    TranslationService.get("clients.gender", "Gender"),
                ]

                table_data = [headers]

                for client in clients_data:
                    birth_date = client.get("birth_date", "")
                    age_str = ""
                    if birth_date:
                        age = CalculationService.calculate_age(birth_date)
                        age_str = str(age) if age is not None else ""

                    gender_raw = (client.get("gender", "") or "").strip()
                    g = gender_raw.lower()
                    if g == "male":
                        gender_translated = TranslationService.get("clients.male", "Male")
                    elif g == "female":
                        gender_translated = TranslationService.get("clients.female", "Female")
                    elif g == "other":
                        gender_translated = TranslationService.get("clients.other", "Other")
                    else:
                        gender_translated = gender_raw

                    table_data.append(
                        [
                            client.get("full_name", ""),
                            client.get("email", ""),
                            client.get("phone", ""),
                            age_str,
                            gender_translated,
                        ]
                    )

                table = Table(
                    table_data,
                    colWidths=[1.8 * inch, 1.8 * inch, 1.2 * inch, 0.7 * inch, 0.8 * inch],
                )

                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), font_bold),
                            ("FONTSIZE", (0, 0), (-1, 0), 11),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),

                            ("FONTNAME", (0, 1), (-1, -1), font_normal),
                            ("FONTSIZE", (0, 1), (-1, -1), 9),
                            ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#9aa0a6")),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                             [colors.white, colors.HexColor("#f5f5f5")]),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ]
                    )
                )

                elements.append(table)

            doc.build(elements)
            return True, TranslationService.get("messages.export_success", "PDF exported successfully!")

        except Exception as e:
            return False, (TranslationService.get("messages.export_error", "Error exporting PDF: ") + str(e))

    @staticmethod
    def backup_to_json(db, output_path):
        """
        Backup all data (clients, diets, measurements) to JSON.
        Returns: (success: bool, message: str)
        """
        try:
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "backup_version": "1.0",
                "collections": {},
            }

            if "clients" in db.list_collection_names():
                clients = list(db["clients"].find())
                backup_data["collections"]["clients"] = [
                    {**doc, "_id": str(doc["_id"])} for doc in clients
                ]

            if "diet_plans" in db.list_collection_names():
                diets = list(db["diet_plans"].find())
                backup_data["collections"]["diet_plans"] = [
                    {**doc, "_id": str(doc["_id"]), "client_id": str(doc.get("client_id", ""))}
                    for doc in diets
                ]

            if "measurements" in db.list_collection_names():
                measurements = list(db["measurements"].find())
                backup_data["collections"]["measurements"] = [
                    {**doc, "_id": str(doc["_id"]), "client_id": str(doc.get("client_id", ""))}
                    for doc in measurements
                ]

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)

            return True, TranslationService.get("messages.backup_success", "Backup created successfully!")

        except Exception as e:
            return False, (TranslationService.get("messages.backup_error", "Error creating backup: ") + str(e))

    @staticmethod
    def restore_from_json(db, input_path):
        """
        Restore data from JSON backup.
        WARNING: This will overwrite existing data!
        Returns: (success: bool, message: str)
        """
        try:
            from bson.objectid import ObjectId

            with open(input_path, "r", encoding="utf-8") as f:
                backup_data = json.load(f)

            collections = backup_data.get("collections", {})

            restored_count = 0
            for collection_name, documents in collections.items():
                if not documents:
                    continue

                if collection_name in db.list_collection_names():
                    db[collection_name].delete_many({})

                    for doc in documents:
                        if "_id" in doc and isinstance(doc["_id"], str):
                            try:
                                doc["_id"] = ObjectId(doc["_id"])
                            except Exception:
                                pass

                        if "client_id" in doc and isinstance(doc["client_id"], str) and doc["client_id"]:
                            try:
                                doc["client_id"] = ObjectId(doc["client_id"])
                            except Exception:
                                pass

                    result = db[collection_name].insert_many(documents)
                    restored_count += len(result.inserted_ids)

            msg = TranslationService.get(
                "messages.restore_success",
                f"Backup restored successfully! ({restored_count} records)"
            )
            return True, msg

        except FileNotFoundError:
            return False, TranslationService.get("messages.file_not_found", "Backup file not found!")
        except json.JSONDecodeError:
            return False, TranslationService.get("messages.invalid_backup_file", "Invalid backup file format!")
        except Exception as e:
            return False, (TranslationService.get("messages.restore_error", "Error restoring backup: ") + str(e))
