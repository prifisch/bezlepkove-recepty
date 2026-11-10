import os
import re
import json
import pandas as pd
import requests

EXCEL_URL = "https://cloud.health.gov.sk/s/WTj7b7fCXoms9H8/download"
OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "v06ce.json")

def parse_weight_in_grams(text):
    if not isinstance(text, str):
        return 0
    text_lower = text.lower()
    kg_match = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", text_lower)
    if kg_match:
        val = float(kg_match.group(1).replace(",", "."))
        return int(val * 1000)
    g_match = re.search(r"(\d+)\s*g", text_lower)
    if g_match:
        return int(g_match.group(1))
    return 0

def main():
    print("Sťahujem aktuálny zoznam z MZ SR...")
    response = requests.get(EXCEL_URL)
    response.raise_for_status()
    
    temp_excel = "temp_zoznam.xlsx"
    with open(temp_excel, "wb") as f:
        f.write(response.content)
    
    print("Načítavam dáta cez pandas...")
    df = pd.read_excel(temp_excel, sheet_name=0)
    
    mask = df.astype(str).apply(lambda col: col.str.contains("V06CE", na=False)).any(axis=1)
    df_v06ce = df[mask].copy()
    
    cleaned_data = []
    for idx, row in df_v06ce.iterrows():
        item = {
            "sukl": str(row.get("Kód ŠÚKL", row.get("Kód", ""))).strip(),
            "nazov": str(row.get("Názov", row.get("Názov a doplnok", ""))).strip(),
            "doplnok": str(row.get("Doplnok", "")).strip(),
            "vyrobca": str(row.get("Držiteľ rozhodnutia", "")).strip(),
            "balenie": str(row.get("Veľkosť balenia", "")).strip(),
            "hmotnost_g": parse_weight_in_grams(str(row.get("Veľkosť balenia", "")) + " " + str(row.get("Doplnok", "")))
        }
        cleaned_data.append(item)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
    
    print(f"Spracovanie úspešné! Uložených {len(cleaned_data)} položiek do {OUTPUT_FILE}")
    
    if os.path.exists(temp_excel):
        os.remove(temp_excel)

if __name__ == "__main__":
    main()
