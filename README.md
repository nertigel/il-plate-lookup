# Israeli Vehicle License Plate Lookup

A Python-based open-source tool that retrieves publicly available vehicle information in Israel using official open datasets from **data.gov.il**.

This project focuses on **accuracy, transparency, caching, and clean presentation**, without using paid APIs or private data sources.

---

## ✨ Features

- 💻 Basic PySide6 GUI
- 🔍 Lookup vehicle data by **Israeli license plate**
- ♿ Detects whether the vehicle is **registered for disability use**
- 🧠 Smart **local cache system** (7 days TTL) to reduce API load
- 📦 Fetches **importer price data** and **importer name**
- 🧾 Clean Hebrew-labeled output
- 🖨️ Generates a **printable HTML report**
- 🆓 Uses **only open government data**

No scraping.  
No private databases.  
No paid APIs.

---

## 📊 Data Fields Returned

The tool maps raw government fields into human-readable Hebrew labels:

```python
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
