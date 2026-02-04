from PySide6 import QtWidgets, QtCore, QtGui
import requests, json, os, time
import html
import webbrowser
from pathlib import Path
from datetime import datetime

# Helper to escape values for HTML
def esc_html(x):
    if x is None:
        return ""
    return html.escape(str(x))

class DataFetcher(QtCore.QThread):
    # Signal to send back the fetched record (dict) and price range (min, max)
    result = QtCore.Signal(dict, float, float, bool, object, object, bool)
    error = QtCore.Signal(str)

    def __init__(self, plate):
        super().__init__()
        self.plate = plate

    def run(self):
        try:
            # CKAN API endpoints and resource IDs
            base_url = "https://data.gov.il/api/3/action/datastore_search"
            veh_res = "053cea08-09bc-40ec-8f7a-156f0677aff3"
            price_res = "39f455bf-6db0-4926-859d-017f34eacbcb"
            details_res = "142afde2-6228-49f9-8a29-9b6c3a0cbe40"
            disability_res = "c8b9f9c8-4612-4068-934f-d4acd2e3c06e"
            count_res = "5e87a7a1-2f6f-41c1-8aec-7216d52a6cf6"

            # Ensure cache directory exists
            cache_dir = "cache"
            os.makedirs(cache_dir, exist_ok=True)

            # 1) Fetch vehicle data (license query)
            cache1 = os.path.join(cache_dir, f"veh_{self.plate}.json")
            # If cache exists and is <7 days old, load it
            if os.path.exists(cache1) and (time.time() - os.path.getmtime(cache1) < 7*24*3600):
                with open(cache1, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                params = {"resource_id": veh_res, "q": str(self.plate), "limit": 10}
                response = requests.get(base_url, params=params)
                data = response.json()
                with open(cache1, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            records = data.get("result", {}).get("records", [])
            if not records:
                # === FALLBACK 1: Personal Import Vehicles ===
                personal_res = "03adc637-b6fe-402b-9937-7c3d3afc9140"
                cache_personal = os.path.join(cache_dir, f"personal_{self.plate}.json")

                if os.path.exists(cache_personal) and (time.time() - os.path.getmtime(cache_personal) < 7*24*3600):
                    with open(cache_personal, 'r', encoding='utf-8') as f:
                        personal_data = json.load(f)
                else:
                    params_personal = {"resource_id": personal_res, "q": str(self.plate), "limit": 1}
                    response_personal = requests.get(base_url, params=params_personal)
                    personal_data = response_personal.json()
                    with open(cache_personal, 'w', encoding='utf-8') as f:
                        json.dump(personal_data, f, ensure_ascii=False, indent=2)

                personal_records = personal_data.get("result", {}).get("records", [])

                if personal_records:
                    records = personal_records  # Treat this as vehicle record
                    # Mark it as personal import type
                    records[0]["personal_import"] = True
                else:
                    records = None

            if not records and not personal_records:
                self.error.emit(f"No data found for plate {self.plate}")
                return
                
            record = records[0]  # use the first matching record

            # 2) Fetch importer price data (using degem_cd and tozeret_cd)
            degem_cd = record.get("degem_cd", 0)
            tozeret_cd = record.get("tozeret_cd", 0)
            shnat_yitzur = record.get("shnat_yitzur", None)
            cache2 = os.path.join(cache_dir, f"price_{degem_cd}_{tozeret_cd}.json")
            if os.path.exists(cache2) and (time.time() - os.path.getmtime(cache2) < 7*24*3600):
                with open(cache2, 'r', encoding='utf-8') as f:
                    price_data = json.load(f)
            else:
                filters = {"degem_cd": [degem_cd], "tozeret_cd": [tozeret_cd]}
                params = {"resource_id": price_res, "filters": json.dumps(filters), "limit": 100}
                response2 = requests.get(base_url, params=params)
                price_data = response2.json()
                with open(cache2, 'w', encoding='utf-8') as f:
                    json.dump(price_data, f, ensure_ascii=False, indent=2)

            cache2_1 = os.path.join(cache_dir, f"details_{degem_cd}_{tozeret_cd}.json")
            if os.path.exists(cache2_1) and (time.time() - os.path.getmtime(cache2_1) < 7*24*3600):
                with open(cache2_1, 'r', encoding='utf-8') as f:
                    details_data = json.load(f)
            else:
                filters = {"degem_cd": [degem_cd], "tozeret_cd": [tozeret_cd], "shnat_yitzur": [shnat_yitzur]}
                params = {"resource_id": details_res, "filters": json.dumps(filters), "limit": 100}
                response2_1 = requests.get(base_url, params=params)
                details_data = response2_1.json()
                with open(cache2_1, 'w', encoding='utf-8') as f:
                    json.dump(details_data, f, ensure_ascii=False, indent=2)

            cache3 = os.path.join(cache_dir, f"disability_{self.plate}.json")
            if os.path.exists(cache3) and (time.time() - os.path.getmtime(cache3) < 7*24*3600):
                with open(cache3, 'r', encoding='utf-8') as f:
                    disability_data = json.load(f)
            else:
                params = {"resource_id": disability_res, "q": str(self.plate), "limit": 5}
                response3 = requests.get(base_url, params=params)
                disability_data = response3.json()
                with open(cache3, 'w', encoding='utf-8') as f:
                    json.dump(disability_data, f, ensure_ascii=False, indent=2)

            # Parse disability response
            disability_records = disability_data.get("result", {}).get("records", [])
            if disability_records:
                dis_tag = disability_records[0]   # use first record
                disability_status = True
                disability_type = dis_tag.get("SUG TAV", "")
                disability_issue_date = dis_tag.get("TAARICH HAFAKAT TAG", "")
            else:
                disability_status = False
                disability_type = None
                disability_issue_date = None

            price_records = price_data.get("result", {}).get("records", [])
            prices = []
            for rec in price_records:
                if record.get("yevuan_rehev") is None:
                    record["yevuan_rehev"] = rec.get("shem_yevuan")

                val = rec.get("mehir")
                if val is not None:
                    try:
                        prices.append(float(val))
                    except:
                        # Try stripping commas if any, e.g. "120,000"
                        try:
                            prices.append(float(val.replace(',', '').strip()))
                        except:
                            pass

            if prices:
                min_price = min(prices)
                max_price = max(prices)
            else:
                min_price = max_price = 0.0

            details_records = details_data.get("result", {}).get("records", [])
            if details_records:
                record_data = details_records[0]  # pick the first record
                record["automatic_ind"] = record_data.get("automatic_ind", "לא רשום")
                record["merkav"] = record_data.get("merkav", "לא רשום")
                record["nefah_manoa"] = record_data.get("nefah_manoa", "לא רשום")
                record["kvuzat_agra_cd"] = record_data.get("kvuzat_agra_cd", "לא רשום")
                record["abs_ind"] = record_data.get("abs_ind", "לא רשום")
                record["kariot_avir_source"] = record_data.get("kariot_avir_source", "לא רשום")
                record["hege_koah_ind"] = record_data.get("hege_koah_ind", "לא רשום")
                record["halonot_hashmal_source"] = record_data.get("halonot_hashmal_source", "לא רשום")
                record["halon_bagg_ind"] = record_data.get("halon_bagg_ind", "לא רשום")
                record["mispar_dlatot"] = record_data.get("mispar_dlatot", "לא רשום")
                record["koah_sus"] = record_data.get("koah_sus", "לא רשום")
                record["mispar_moshavim"] = record_data.get("mispar_moshavim", "לא רשום")
                record["bakarat_yatzivut_ind"] = record_data.get("bakarat_yatzivut_ind", "לא רשום")
                record["kosher_grira_im_blamim"] = record_data.get("kosher_grira_im_blamim", "לא רשום")
                record["kosher_grira_bli_blamim"] = record_data.get("kosher_grira_bli_blamim", "לא רשום")
                record["kvutzat_zihum"] = record_data.get("kvutzat_zihum", "לא רשום")
                record["bakarat_stiya_menativ_ind"] = record_data.get("bakarat_stiya_menativ_ind", "לא רשום")
                record["nitur_merhak_milfanim_ind"] = record_data.get("nitur_merhak_milfanim_ind", "לא רשום")
                record["zihuy_beshetah_nistar_ind"] = record_data.get("zihuy_beshetah_nistar_ind", "לא רשום")
            
            # Emit the results back to the main thread
            self.result.emit(
                record,
                min_price,
                max_price,
                disability_status,
                disability_type,
                disability_issue_date,
                record.get("personal_import", False)
            )

        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vehicle Lookup")

        # Input for license plate
        self.input = QtWidgets.QLineEdit()
        self.input.setPlaceholderText("Enter license plate")
        # Search button
        self.search_btn = QtWidgets.QPushButton("Search")
        self.search_btn.clicked.connect(self.search_plate)
        # Export to HTML button (disabled until we have data)
        self.export_btn = QtWidgets.QPushButton("Export to HTML")
        self.export_btn.clicked.connect(self.export_html)
        self.export_btn.setEnabled(False)

        # Table to display vehicle info
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        # Header labels (Hebrew: "מס' רכב"=Plate, "יצרן"=Make, "דגם"=Model, "שנה"=Year, "צבע"=Color)
        self.table.setHorizontalHeaderLabels(["מס' רכב", "יצרן", "דגם", "שנה", "צבע", "מס' שלדה"])
        self.table.verticalHeader().setVisible(False)

        # Label to show importer price range
        self.price_label = QtWidgets.QLabel("מחיר יבואן: -")

        # Layout setup
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addWidget(self.input)
        top_layout.addWidget(self.search_btn)

        central_layout = QtWidgets.QVBoxLayout()
        central_layout.addLayout(top_layout)
        central_layout.addWidget(self.table)
        central_layout.addWidget(self.price_label)
        central_layout.addWidget(self.export_btn)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)

        # Hold the current record and prices
        self.current_record = None
        self.current_min_price = 0.0
        self.current_max_price = 0.0

    def search_plate(self):
        plate = self.input.text().strip()
        if not plate:
            QtWidgets.QMessageBox.warning(self, "Error", "Please enter a license plate.")
            return
        self.search_btn.setEnabled(False)
        self.price_label.setText("מחפש...")  # "Searching..."
        # Start the data fetcher thread
        self.worker = DataFetcher(plate)
        self.worker.result.connect(self.handle_results)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def handle_results(self, record, min_price, max_price, disability_status, disability_type, disability_issue_date, personal_import):
        # Re-enable search button
        self.search_btn.setEnabled(True)
        self.current_record = record
        self.current_min_price = min_price
        self.current_max_price = max_price
        self.disability_status = disability_status
        self.disability_type = disability_type
        self.disability_issue_date = disability_issue_date
        self.personal_import = personal_import

        vehicle_id_number = record.get("misgeret", "") or record.get("shilda", "")

        # Populate the table (one row with fields from record)
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QtWidgets.QTableWidgetItem(str(record.get("mispar_rechev", ""))))
        self.table.setItem(0, 1, QtWidgets.QTableWidgetItem(record.get("tozeret_nm", "")))
        self.table.setItem(0, 2, QtWidgets.QTableWidgetItem(record.get("degem_nm", "")))
        self.table.setItem(0, 3, QtWidgets.QTableWidgetItem(str(record.get("shnat_yitzur", ""))))
        self.table.setItem(0, 4, QtWidgets.QTableWidgetItem(record.get("tzeva_rechev", "לא רשום")))
        self.table.setItem(0, 5, QtWidgets.QTableWidgetItem(vehicle_id_number))
        self.table.resizeColumnsToContents()

        # Display the price range
        if min_price == max_price == 0.0:
            self.price_label.setText("מחיר יבואן לא נמצא")
        else:
            self.price_label.setText(f"מחיר יבואן: ₪{int(min_price)}–₪{int(max_price)}")

        if disability_status:
            self.price_label.setText(self.price_label.text() + " | תג נכה: קיים")
        else:
            self.price_label.setText(self.price_label.text() + " | תג נכה: אין")

        if self.personal_import:
            self.price_label.setText(self.price_label.text() + " | יבוא אישי")

        self.export_btn.setEnabled(True)

    def handle_error(self, msg):
        self.search_btn.setEnabled(True)
        QtWidgets.QMessageBox.warning(self, "Error", msg)
        self.price_label.setText("שגיאה בחיפוש")  # "Search error"

    def export_html(self):
        record = self.current_record or {}

        if not record or record == {}:
            QtWidgets.QMessageBox.warning(self, "Error", "No data to export.")
            return
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save HTML", esc_html(record.get("mispar_rechev", "")) or "", "HTML Files (*.html)")
        if filename:
            self.generate_html(filename)

    def generate_html(self, filepath):
        record = self.current_record or {}
        min_price = self.current_min_price or 0
        max_price = self.current_max_price or 0

        out_path = Path(filepath)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Identify vehicle ID number
        vehicle_id_number = record.get("misgeret", "") or record.get("shilda", "")

        # A cleaner label mapping for better display
        label_map = {
            "mispar_rechev": "מספר רכב",
            "tozeret_nm": "יצרן",
            "degem_nm": "דגם",
            "degem_manoa": "דגם מנוע",
            "shnat_yitzur": "שנת יצור",
            "tzeva_rechev": "צבע",
            "sug_delek_nm": "סוג דלק",
            "merkav": "מבנה רכב",
            "nefach_manoa": "נפח מנוע",
            "koah_sus": "כוח סוס",
            "mispar_dlatot": "מספר דלתות",
            "mispar_moshavim": "מספר מושבים",
            "baalut": "בעלות",
            "tokef_dt": "תוקף רישום",
            "mivchan_acharon_dt": "מבחן אחרון",
            "kvuzat_agra_cd": "קבוצת רישוי",
            "automatic_ind": "תיבת הילוכים אוטומטית",
            "abs_ind": "מערכת בלימה ABS",
            "hege_koah_ind": "הגה כוח",
            "kariot_avir_source": "כמות כריות אוויר",
            "bakarat_stiya_menativ_ind": "בקרת סטייה מנתיב",
            "bakarat_yatzivut_ind": "בקרת יציבות",
            "halon_bagg_ind": "חלון בגג",
            "nitur_merhak_milfanim_ind": "ניטור מרחק מלפנים",
            "zihuy_beshetah_nistar_ind": "זיהוי בשטח נסתר",
        }

        display_pairs = []

        # Top-priority fields for General Info
        display_pairs.append(("מס' שלדה/מנוע", esc_html(vehicle_id_number)))
        for key in ["mispar_rechev", "tozeret_nm", "degem_manoa", "degem_nm", "shnat_yitzur", "tzeva_rechev", "sug_delek_nm"]:
            if record.get(key):
                display_pairs.append((label_map.get(key, key), esc_html(record.get(key))))

        # Disability status
        if self.disability_status:
            display_pairs.append(("תג נכה", "<i class='bi bi-check-circle-fill' style='color:green'></i>"))
            display_pairs.append(("סוג תג", esc_html(self.disability_type)))
            display_pairs.append(("תאריך הפקה", esc_html(self.disability_issue_date)))
        else:
            display_pairs.append(("תג נכה", "<i class='bi bi-x-circle-fill' style='color:red'></i>"))

        # Personal import
        display_pairs.append(("ייבוא אישי", "<i class='bi bi-check-circle-fill' style='color:green'></i>" if getattr(self, 'personal_import', False) else "<i class='bi bi-x-circle-fill' style='color:red'></i>"))

        # Other structured fields
        for key in ["merkav", "nefach_manoa", "koah_sus", "mispar_dlatot", "mispar_moshavim", "baalut",
                    "tokef_dt", "mivchan_acharon_dt", "kvuzat_agra_cd", "kariot_avir_source"]:
            if record.get(key):
                display_pairs.append((label_map.get(key, key), esc_html(record.get(key))))

        # Icon rendering for *_ind fields (binary Yes/No)
        for k, v in record.items():
            if k.endswith("_ind"):
                label = label_map.get(k, k.replace("_ind", "").strip())
                icon = "<i class='bi bi-check-circle-fill' style='color:green'></i>" if str(v) == "1" else "<i class='bi bi-x-circle-fill' style='color:red'></i>"
                display_pairs.append((label, icon))

        # Append *_nm fields not already included
        for k, v in record.items():
            if k.endswith("_nm") and v and label_map.get(k) is None:
                display_pairs.append((esc_html(k.replace("_nm", "")), esc_html(v)))

        # Price handling (unchanged logic)
        if min_price == max_price == 0:
            price_text = "מחיר יבואן: לא זמין"
            price_low = price_high = None
        else:
            try:
                low = float(min_price)
                high = float(max_price)
            except Exception:
                low = high = 0
            price_text = f"מחיר יבואן משוער: ₪{int(low):,} – ₪{int(high):,}" if low != high else f"מחיר יבואן משוער: ₪{int(low):,}"
            price_low, price_high = low, high

        # CSS / HTML template (unchanged except for sections)
        css = """
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <style>
        @media print {
            .page { page-break-after: always; }
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial;
            margin: 20px;
            direction: rtl;
            background: #f5f6fa;
            color: #111;
        }
        .container {
            max-width: 900px;
            margin: auto;
            padding: 20px;
        }
        header {
            text-align: center;
            margin-bottom: 20px;
        }
        header h1 {
            font-size: 24px;
            letter-spacing: 0.5px;
            background: linear-gradient(90deg,#2bb7ff,#0066cc);
            -webkit-background-clip: text;
            color: transparent;
        }
        header .meta {
            font-size: 13px;
            color: #666;
            margin-top: 4px;
        }

        .section {
            background: #fff;
            border-radius: 10px;
            padding: 18px;
            margin-bottom: 18px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }

        .section h2 {
            font-size: 16px;
            margin-bottom: 12px;
            color: #0066cc;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .section h2 i { font-size: 18px; }

        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px 20px;
        }
        .grid-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px dashed #eaecef;
        }
        .grid-item:last-child { border-bottom: none; }
        .label {
            font-weight: 600;
            color: #333;
        }
        .value {
            direction: ltr;
            text-align: left;
            color: #111;
        }
        .price-block {
            margin-top: 16px;
            display: flex;
            gap: 12px;
            align-items: center;
        }
        .price-text { font-weight: 700; color: #0b5ed7; }
        .price-bar {
            flex: 1;
            height: 18px;
            background: #eee;
            border-radius: 10px;
            overflow: hidden;
            position: relative;
        }
        .price-fill {
            height: 100%;
            background: linear-gradient(90deg,#2bb7ff,#0066cc);
            width: 0%;
            transition: width 400ms ease;
        }
        .footer {
            margin-top: 24px;
            font-size: 12px;
            color: #777;
            text-align: center;
        }
        a { color: #0b5ed7; }
        </style>
        """

        # Price bar fill percentage logic: if we have min and max show relative fill for min/max
        price_bar_html = ""
        if price_low is not None and price_high is not None and price_high > 0:
            # percentage of min relative to max (0-100)
            pct = int((price_low / price_high) * 100) if price_high > 0 else 0
            # two markers: low and high printed next to bar
            price_bar_html = f"""
            <div class="price-block">
                <div class="price-text">{esc_html(price_text)}</div>
                <div class="price-text">יובא על ידי: {esc_html(record["yevuan_rehev"])}</div>
                <div class="price-bar" aria-hidden="true">
                <div class="price-fill" style="width:{pct}%"></div>
                </div>
                <div style="min-width:120px;text-align:left;font-size:13px;color:#333;">
                <div>נמוך: ₪{int(price_low):,}</div>
                <div>גבוה: ₪{int(price_high):,}</div>
                </div>
            </div>
            """
        else:
            price_bar_html = f"<div class='price-block'><div class='price-text'>{esc_html(price_text)}</div></div>"

        rows_html = [
            f"<div class='grid-item'><span class='label'>{label}</span><span class='value'>{value}</span></div>"
            for label, value in display_pairs
        ]

        # Better grouping — dynamic slicing
        sections_html = f"""
        <div class='section'>
            <h2><i class='bi bi-info-circle'></i> פרטים כלליים</h2>
            <div class='grid'>{''.join(rows_html[:10])}</div>
        </div>
        <div class='section'>
            <h2><i class='bi bi-card-list'></i> רישוי ובעלות</h2>
            <div class='grid'>{''.join(rows_html[10:15])}</div>
        </div>
        <div class='section'>
            <h2><i class='bi bi-gear'></i> מפרט טכני</h2>
            <div class='grid'>{''.join(rows_html[15:22])}</div>
        </div>
        <div class='section'>
            <h2><i class='bi bi-shield-check'></i> מערכות בטיחות ופיצ'רים</h2>
            <div class='grid'>{''.join(rows_html[22:])}</div>
        </div>
        """

        now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_doc = f"""<!doctype html>
        <html lang="he">
        <head>
            <meta charset="utf-8">
            <title>דו"ח רכב - {esc_html(record.get('mispar_rechev',''))}</title>
            {css}
        </head>
        <body>
        <div class="container page">
            <header>
                <h1>דו"ח איתור וניתוח רכב</h1>
                <div class="meta">נוצר: {now_s} — מקור: data.gov.il</div>
            </header>

            <div class="intro">
                מסמך זה מציג את תוצאות החיפוש, המיון והעיבוד עבור מספר רכב מבוקש. המידע נלקח ממאגרי מידע ציבוריים ומשקף את מצב הרכב כפי שנרשם.
            </div>

            {sections_html}

            {price_bar_html}

            <div class="footer">דוח זה נוצר אוטומטית. מידע זה אינו מהווה תחליף לבדיקה מקצועית.</div>
        </div>
        </body>
        </html>
        """

        out_path.write_text(html_doc, encoding="utf-8")

        try:
            webbrowser.open(out_path.resolve().as_uri())
        except Exception:
            pass

        return str(out_path)

def show_welcome_message():
    msg = QtWidgets.QMessageBox()
    msg.setWindowTitle("Vehicle License Plate Indexing | קבלת פנים")
    msg.setIcon(QtWidgets.QMessageBox.Information)

    msg.setText(
        "Welcome to the Vehicle License Plate Indexing System!\n"
        "This application allows efficient searching, organizing, and indexing of vehicle plate data using modern UI and automated logic.\n\n"
        "ברוכים הבאים למערכת לאינדוקס לוחיות רישוי!\n"
        "באמצעות תוכנה זו ניתן לבצע חיפוש, סידור ואינדוקס חכם של נתוני רכבים בצורה יעילה, אינטואיטיבית ומהירה.\n\n"
        "Credits:\n"
        " * Design & Development: github.com/nertigel.\n"
        " * Powered by data.gov.il / Qt / Python / AI-assisted logic.\n\n"
        "Have a productive experience!"
    )

    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg.exec()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    
    # Set icon for the running application
    app.setWindowIcon(QtGui.QIcon("assets/app.ico"))

    show_welcome_message()

    window = MainWindow()
    window.resize(600, 400)
    window.show()
    app.exec()