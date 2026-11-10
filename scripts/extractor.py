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
    if "V06CE" in row_str or "ŠÚKL" in row_str or "Kód" in row_str:
      header_row_idx = idx
      break

  print(f"Hlavička nájdená na riadku: {header_row_idx}")
  df = pd.read_excel(temp_excel, sheet_name=0, header=header_row_idx)
  print("Dostupné stĺpce v exceli:", list(df.columns))

  cleaned_data = []

  for idx, row in df.iterrows():
    values = [str(val).strip() for val in row.values if pd.notna(val)]
    if not values:
      continue

    # Riadok musí patriť do kategórie V06CE
    is_v06ce = any("V06CE" in str(val) for val in row.values)
    if not is_v06ce:
      continue

    sukl = ""
    nazov = ""
    doplnok = ""
    vyrobca = ""
    balenie = ""

    # Vyhľadanie podľa názvov stĺpcov
    for col in df.columns:
      col_lower = str(col).lower()
      val = row.get(col)
      if pd.isna(val):
        continue
      val_str = str(val).strip()

      if "šúkl" in col_lower or "kód" in col_lower or "kod" in col_lower:
        if val_str and val_str.upper() not in [
            "V06CE",
            "V06CEX",
            "V06CEY",
            "V06CEX1",
            "V06CEY1",
        ]:
          sukl = val_str
      elif "názov" in col_lower or "nazov" in col_lower:
        if not nazov:
          nazov = val_str
      elif "doplnok" in col_lower or "doplnenie" in col_lower:
        doplnok = val_str
      elif (
          "držit" in col_lower
          or "vyrob" in col_lower
          or "drzitel" in col_lower
      ):
        vyrobca = val_str
      elif "balenie" in col_lower or "veľkosť" in col_lower:
        balenie = val_str

    # Heuristika pre ŠÚKL kód, ak sa nenašiel cez názov stĺpca
    if not sukl or sukl.upper().startswith("V06CE"):
      for val in values:
        if (
            re.match(r"^[0-9A-Z]{5,10}$", val)
            and not val.upper().startswith("V06CE")
        ):
          sukl = val
          break

    # Ak je to stále len hlavička kategórie, preskočíme
    if not sukl or sukl.upper().startswith("V06CE"):
      continue

    # Doplnenie názvu, ak chýba
    if not nazov:
      for val in values:
        if len(val) > 4 and val != sukl and "V06CE" not in val:
          nazov = val
          break

    # Doplnenie balenia, ak chýba
    if not balenie:
      for val in values:
        if any(
            unit in val.lower() for unit in ["g", "kg", "ml", "ks", "tbl"]
        ):
          balenie = val
          break

    item = {
        "sukl": sukl,
        "nazov": nazov if nazov else "Bezlepková potravina",
        "doplnok": doplnok,
        "vyrobca": vyrobca,
        "balenie": balenie if balenie else "",
        "hmotnost_g": parse_weight_in_grams(f"{balenie} {doplnok}"),
    }

    if item["sukl"] and not any(
        x["sukl"] == item["sukl"] for x in cleaned_data
    ):
      cleaned_data.append(item)

  os.makedirs(OUTPUT_DIR, exist_ok=True)
  with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

  print(f"Uložených {len(cleaned_data)} reálnych produktov do {OUTPUT_FILE}")

  if os.path.exists(temp_excel):
    os.remove(temp_excel)


if __name__ == "__main__":
  main()
