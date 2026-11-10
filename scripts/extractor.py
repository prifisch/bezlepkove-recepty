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
    
    print("Načítavam dáta a detegujem hlavičku tabuľky...")
    df_raw = pd.read_excel(temp_excel, sheet_name=0, header=None)
    
    header_row_idx = 0
    for idx, row in df_raw.head(15).iterrows():
        row_str = " ".join(str(val) for val in row.values)
        if "V06CE" in row_str or "ŠÚKL" in row_str or "Kód" in row_str or "Názov" in row_str:
            header_row_idx = idx
            break
            
    print(f"Hlavička nájdená na riadku index: {header_row_idx}")
    
    df = pd.read_excel(temp_excel, sheet_name=0, header=header_row_idx)
    
    mask = df.astype(str).apply(lambda col: col.str.contains("V06CE", na=False)).any(axis=1)
    df_v06ce = df[mask].copy()
    
    print(f"Nájdených {len(df_v06ce)} riadkov s kategóriou V06CE.")
    
    cleaned_data = []
    for idx, row in df_v06ce.iterrows():
        def get_col(*names):
            for name in names:
                for col in df.columns:
                    if name.lower() in str(col).lower():
                        val = row.get(col)
                        if pd.notna(val):
                            return str(val).strip()
            return ""

        sukl = get_col("ŠÚKL", "Kód", "Kod")
        nazov = get_col("Názov", "Nazov")
        doplnok = get_col("Doplnok", "Doplnenie")
        vyrobca = get_col("Držiteľ", "Výrobca", "Drzitel")
        balenie = get_col("Balenie", "Veľkosť", "Velkost")

        if not sukl or sukl == "nan":
            for val in row.values:
                val_str = str(val).strip()
                if re.match(r"^[0-9A-Z]{5,8}$", val_str):
                    sukl = val_str
                    break

        # DÔLEŽITÉ: Preskočíme riadky, ktoré sú len skupinovými hlavičkami (začínajú na V06CE)
        if sukl.upper().startswith("V06CE") or not sukl or sukl == "nan":
            continue

        item = {
            "sukl": sukl,
            "nazov": nazov if nazov and nazov != "nan" else "Bez názvu",
            "doplnok": doplnok if doplnok != "nan" else "",
            "vyrobca": vyrobca if vyrobca != "nan" else "",
            "balenie": balenie if balenie != "nan" else "",
            "hmotnost_g": parse_weight_in_grams(str(balenie) + " " + str(doplnok))
        }
        cleaned_data.append(item)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
    
    print(f"Uložených {len(cleaned_data)} reálnych produktov do {OUTPUT_FILE}")
    
    if os.path.exists(temp_excel):
        os.remove(temp_excel)

if __name__ == "__main__":
    main()
