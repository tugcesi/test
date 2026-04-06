#!/usr/bin/env python3
"""
Simulate missing values for istanbul_kiralik_complete.csv
and produce istanbul_kiralik_simulated.csv
"""

import csv
import random
import re

INPUT_FILE = "istanbul_kiralik_complete.csv"
OUTPUT_FILE = "istanbul_kiralik_simulated.csv"

# District tiers
LUXURY_DISTRICTS = {
    "beşiktaş", "sarıyer", "şişli", "nişantaşı", "teşvikiye",
    "kadıköy", "moda", "caddebostan", "bakırköy", "florya",
    "beyoğlu", "cihangir", "maslak", "istinye", "etiler", "levent",
    "balmumcu", "bebek", "arnavutköy",  # Arnavutköy here = Beşiktaş ilçesi neighbourhood
}

MID_DISTRICTS = {
    "ataşehir", "üsküdar", "kağıthane", "maltepe", "kartal",
    "ümraniye", "başakşehir", "bahçelievler", "küçükçekmece",
    "pendik", "sancaktepe", "çekmeköy", "tuzla", "avcılar",
    "eyüpsultan", "beylikdüzü", "bağcılar", "gaziosmanpaşa",
    "fatih", "zeytinburnu", "güngören", "ataşehir",
}

SUBURB_DISTRICTS = {
    "arnavutköy", "silivri", "çatalca", "şile", "sultanbeyli",
    "sultangazi", "esenyurt", "büyükçekmece", "esenler",
    "bayrampaşa",
}


def get_district_tier(konum: str) -> str:
    """Return 'luxury', 'mid', or 'suburb' based on district name in konum."""
    konum_lower = konum.lower()
    for d in LUXURY_DISTRICTS:
        if d in konum_lower:
            return "luxury"
    for d in SUBURB_DISTRICTS:
        if d in konum_lower:
            return "suburb"
    for d in MID_DISTRICTS:
        if d in konum_lower:
            return "mid"
    return "mid"  # default


def extract_room_count(baslik: str) -> str:
    """Extract room info like '2+1', '3+1', '1+0' from title."""
    match = re.search(r"\b(\d+\+\d+)\b", baslik)
    if match:
        return match.group(1)
    return "2+1"


def is_villa_like(baslik: str, oda: str) -> bool:
    """Check if the listing is villa/müstakil/yalı type."""
    b = baslik.lower()
    # Use word-boundary-aware checks to avoid false matches (e.g. 'yalı' inside 'eşyalı')
    for keyword in ["villa", "müstakil", "tripleks", "dublex", "dubleks"]:
        if re.search(r"\b" + re.escape(keyword) + r"\b", b):
            return True
    # 'yalı' needs special handling: must be standalone word, not inside 'eşyalı'
    if re.search(r"(?<![a-zçğıöşüa-z])yalı\b", b):
        return True
    return False


def simulate_metrekare(baslik: str, oda: str) -> str:
    """Simulate m2 based on room count and title hints."""
    # Check title for explicit m² value (2-4 digits before m² or M2)
    # Skip if this appears to be a balcony/garden/arsa area (followed by balkon/bahçe/arsa)
    for m in re.finditer(r"(\d{2,4})\s*m[²2]", baslik, re.IGNORECASE):
        val = int(m.group(1))
        # Check what follows to exclude balcony/garden sizes
        after = baslik[m.end():].lower().strip()
        if re.match(r"[\s,]*balkon", after):
            continue
        # Reasonable apartment/house range: 20–2000 m²
        if 20 <= val <= 2000:
            return str(val)


    if is_villa_like(baslik, oda):
        return str(random.randint(250, 500))

    ranges = {
        "1+0": (25, 45),
        "1+1": (45, 75),
        "2+1": (70, 110),
        "3+1": (100, 145),
        "4+1": (140, 200),
        "4+2": (180, 280),
        "5+1": (180, 280),
        "5+2": (180, 280),
    }
    lo, hi = ranges.get(oda, (180, 280))
    # For large room counts not in map
    first = oda.split("+")[0] if "+" in oda else "2"
    try:
        n = int(first)
    except ValueError:
        n = 2
    if n >= 6:
        lo, hi = 250, 500
    return str(random.randint(lo, hi))


def simulate_kat(baslik: str) -> str:
    """Simulate floor number."""
    b = baslik.lower()
    if "zemin" in b or "giriş" in b:
        return str(random.choice([0, 1]))
    if "çatı" in b or "teras" in b:
        return str(random.randint(10, 12))
    if "dubleks" in b or "dublex" in b or "tripleks" in b:
        return str(random.randint(3, 10))
    return str(random.randint(1, 12))


def simulate_fiyat(baslik: str, oda: str, tier: str) -> str:
    """Simulate monthly rent price."""
    # Check title for explicit price
    price_match = re.search(r"(\d[\d\.\s]*)\s*[Tt][Ll]", baslik)
    if price_match:
        raw = price_match.group(1).replace(".", "").replace(" ", "")
        try:
            return str(int(raw))
        except ValueError:
            pass

    villa = is_villa_like(baslik, oda)
    first = oda.split("+")[0] if "+" in oda else "2"
    try:
        n = int(first)
    except ValueError:
        n = 2

    if tier == "luxury":
        if villa:
            lo, hi = 200000, 800000
        elif oda == "1+0":
            lo, hi = 18000, 28000
        elif oda == "1+1":
            lo, hi = 25000, 55000
        elif oda == "2+1":
            lo, hi = 45000, 90000
        elif oda == "3+1":
            lo, hi = 75000, 160000
        else:
            lo, hi = 120000, 300000
    elif tier == "suburb":
        if villa:
            lo, hi = 80000, 200000
        elif oda == "1+0":
            lo, hi = 7000, 13000
        elif oda == "1+1":
            lo, hi = 10000, 22000
        elif oda == "2+1":
            lo, hi = 18000, 38000
        elif oda == "3+1":
            lo, hi = 30000, 60000
        else:
            lo, hi = 50000, 100000
    else:  # mid
        if villa:
            lo, hi = 120000, 300000
        elif oda == "1+0":
            lo, hi = 10000, 18000
        elif oda == "1+1":
            lo, hi = 15000, 32000
        elif oda == "2+1":
            lo, hi = 28000, 55000
        elif oda == "3+1":
            lo, hi = 45000, 85000
        else:
            lo, hi = 75000, 140000

    # Round to nearest 500
    val = random.randint(lo, hi)
    val = round(val / 500) * 500
    return str(val)


def simulate_yapi_yasi(baslik: str) -> str:
    """Simulate building age."""
    b = baslik.lower()
    if any(k in b for k in ["sıfır", "yeni bina", "yeni yapı", "2024", "2025", "2026"]):
        return str(random.choice([0, 1]))
    age_match = re.search(r"(\d+)\s*yıllık", b)
    if age_match:
        return age_match.group(1)
    return str(random.randint(0, 25))


def simulate_esya(baslik: str) -> str:
    """Simulate furnished status."""
    b = baslik.lower()
    if any(k in b for k in ["eşyalı", "mobilyalı", "full eşya", "full mobilya"]):
        return "Eşyalı"
    if any(k in b for k in ["eşyasız", "boş daire", "boş ev"]):
        return "Eşyasız"
    return "Eşyalı" if random.random() < 0.40 else "Eşyasız"


def simulate_isitma(baslik: str, tier: str) -> str:
    """Simulate heating type."""
    b = baslik.lower()
    if any(k in b for k in ["kombili", "kombi"]):
        return "Kombi"
    if any(k in b for k in ["merkezi ısıtma", "merkezi sistem", "merkezi"]):
        return "Merkezi"
    if "yerden ısıtma" in b:
        return "Yerden Isıtma"
    if "klima" in b:
        return "Klima (Split)"

    if tier == "luxury":
        choices = ["Kombi", "Merkezi", "Yerden Isıtma", "Klima (Split)"]
        weights = [50, 30, 10, 10]
    elif tier == "suburb":
        choices = ["Kombi", "Soba/Doğalgaz", "Merkezi", "Klima (Split)"]
        weights = [60, 20, 10, 10]
    else:
        choices = ["Kombi", "Merkezi", "Soba/Doğalgaz", "Klima (Split)"]
        weights = [50, 30, 10, 10]

    total = sum(weights)
    r = random.randint(1, total)
    cumulative = 0
    for choice, w in zip(choices, weights):
        cumulative += w
        if r <= cumulative:
            return choice
    return choices[0]


def process_row(row: dict, index: int) -> dict:
    """Fill missing values in a row using simulation rules."""
    random.seed(index)

    baslik = row.get("Başlık", "")
    konum = row.get("Konum", "")
    tier = get_district_tier(konum)

    # Oda Sayısı
    oda = row.get("Oda Sayısı", "").strip()
    if not oda:
        oda = extract_room_count(baslik)
        row["Oda Sayısı"] = oda

    # Metrekare
    if not row.get("Metrekare", "").strip():
        row["Metrekare"] = simulate_metrekare(baslik, oda)

    # Kat
    if not row.get("Kat", "").strip():
        row["Kat"] = simulate_kat(baslik)

    # Fiyat
    if not row.get("Fiyat", "").strip():
        row["Fiyat"] = simulate_fiyat(baslik, oda, tier)

    # Yapı Yaşı
    if not row.get("Yapı Yaşı", "").strip():
        row["Yapı Yaşı"] = simulate_yapi_yasi(baslik)

    # Eşya
    if not row.get("Eşya", "").strip():
        row["Eşya"] = simulate_esya(baslik)

    # Isıtma
    if not row.get("Isıtma", "").strip():
        row["Isıtma"] = simulate_isitma(baslik, tier)

    return row


def main():
    with open(INPUT_FILE, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    processed = []
    for i, row in enumerate(rows):
        processed.append(process_row(row, i))

    with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processed)

    print(f"Done. {len(processed)} rows written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
