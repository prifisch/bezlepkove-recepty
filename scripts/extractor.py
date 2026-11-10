import json
import os
import re
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

def get_product_image_url(nazov, vyrobca):
    """
    Vygeneruje relevantný obrázok produktu na základe názvu a výrobcu
    (využíva overené ilustračné a produktové zdroje).
    """
    nazov_l = nazov.lower()
    vyrobca_l = vyrobca.lower()
    
    # Priradenie reálnych alebo reprezentatívnych obrázkov podľa kľúčových slov / značiek
    if "schär" in vyrobca_l or "schaer" in nazov_l:
        if "chlieb" in nazov_l or "bread" in nazov_l:
            return "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=300&auto=format&fit=crop&q=60"
        elif "cestovin" in nazov_l or "spaghet" in nazov_l:
            return "https://images.unsplash.com/photo-1621996346565-e3d5d6281229?w=300&auto=format&fit=crop&q=60"
        else:
            return "https://images.unsplash.com/photo-1589367920969-ab8e050bbc04?w=300&auto=format&fit=crop&q=60"
    elif "múk" in nazov_l or "zmes" in nazov_l or "škrob" in nazov_l:
        return "https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=300&auto=format&fit=crop&q=60"
    elif "chlieb" in nazov_l or "pečivo" in nazov_l or "žeml" in nazov_l:
        return "https://images.unsplash.com/photo-1549931319-a545dcf3bc73?w=300&auto=format&fit=crop&q=60"
    elif "cestovin" in nazov_l or "rezanc" in nazov_l or "špaget" in nazov_l:
        return "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=300&auto=format&fit=crop&q=60"
    elif "suchár" in nazov_l or "piškót" in nazov_l or "sušienk" in nazov_l:
        return "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=300&auto=format&fit=crop&q=60"
    
    return "https://images.unsplash.com/photo-1584799015956-62776c5b966c?w=300&auto=format&fit=crop&q=60"

def main():
    print("Sťahujem aktuálny zoznam z MZ SR...")
    response = requests.get(EXCEL_URL)
    response.raise_for_status()
    
    temp_excel = "temp_zoznam.xlsx"
    with open(temp_excel, "wb") as f:
        f.write(response.content)
    
    print("Načítavam dáta...")
    df_raw = pd.read_excel(temp_excel, sheet_name=0, header=None)
    
    header_row_idx = 0
    for idx, row in df_raw.head(25).iterrows():
        row_str = " ".join(str(val) for val in row.values)
        if "ŠÚKL" in row_str or "Kód" in row_str or "Názov" in row_str:
            header_row_idx = idx
            break
            
    print(f"Hlavička nájdená na riadku: {header_row_idx}")
    df = pd.read_excel(temp_excel, sheet_name=0, header=header_row_idx)
    
    cleaned_data = []
    in_v06ce_section = False
    
    for idx, row in df.iterrows():
        row_str = " ".join(str(val) for val in row.values if pd.notna(val))
        
        if "V06CE" in row_str:
            in_v06ce_section = True
            continue
            
        if in_v06ce_section:
            if any(cat in row_str for cat in ["V06A", "V06B", "V06C", "V06D", "V07", "V08", "A01", "B01", "J01"]) and "V06CE" not in row_str:
                in_v06ce_section = False
                continue
                
        if not in_v06ce_section:
            continue
            
        sukl = ""
        nazov = ""
        doplnok = ""
        vyrobca = ""
        balenie = ""
        
        for col in df.columns:
            col_lower = str(col).lower()
            val = row.get(col)
            if pd.isna(val): continue
            val_str = str(val).strip()
            
            if "šúkl" in col_lower or "kód" in col_lower or "kod" in col_lower:
                if val_str and val_str.upper() not in ["V06CE", "V06CEX", "V06CEY", "V06CEX1", "V06CEY1"]:
                    sukl = val_str
            elif "názov" in col_lower or "nazov" in col_lower:
                if not nazov: nazov = val_str
            elif "doplnok" in col_lower or "doplnenie" in col_lower:
                doplnok = val_str
            elif "držit" in col_lower or "vyrob" in col_lower or "drzitel" in col_lower:
                vyrobca = val_str
            elif "balenie" in col_lower or "veľkosť" in col_lower:
                balenie = val_str
                
        if not sukl:
            for val in row.values:
                val_str = str(val).strip()
                if re.match(r"^[0-9A-Z]{5,10}$", val_str) and val_str not in ["V06CE", "V06CEX", "V06CEY"]:
                    sukl = val_str
                    break
                    
        if not sukl or sukl.upper().startswith("V06CE"):
            continue
            
        if not nazov:
            for val in row.values:
                val_str = str(val).strip()
                if len(val_str) > 3 and val_str != sukl:
                    nazov = val_str
                    break
                    
        if not balenie:
            for val in row.values:
                val_str = str(val).strip()
                if any(unit in val_str.lower() for unit in ["g", "kg", "ml", "ks", "tbl"]):
                    balenie = val_str
                    break
                    
        clean_nazov = nazov if nazov else "Bezlepková potravina"
        clean_vyrobca = vyrobca if pd.notna(vyrobca) else ""
        
        item = {
            "sukl": sukl,
            "nazov": clean_nazov,
            "doplnok": doplnok if pd.notna(doplnok) else "",
            "vyrobca": clean_vyrobca,
            "balenie": balenie if pd.notna(balenie) else "",
            "hmotnost_g": parse_weight_in_grams(f"{balenie} {doplnok}"),
            "image": get_product_image_url(clean_nazov, clean_vyrobca)
        }
        
        if item["sukl"] and not any(x["sukl"] == item["sukl"] for x in cleaned_data):
            cleaned_data.append(item)
            
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
        
    print(f"Uložených {len(cleaned_data)} reálnych produktov s obrázkami do {OUTPUT_FILE}")
    
    if os.path.exists(temp_excel):
        os.remove(temp_excel)

if __name__ == "__main__":
    main()
