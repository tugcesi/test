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

# Neighbourhood-level overrides (checked BEFORE district-level rules)
# Sarıyer neighbourhoods
_SARIYE_MID_MAHALLELER = {
    "tarabya", "ferahevler", "kireçburnu", "cumhuriyet",
    "çamlıtepe", "bahçeköy", "zekeriyaköy", "büyükdere",
    "rumeli kavağı", "reşitpaşa", "çayırbaşı", "uskumruköy",
}
_SARIYE_LUXURY_MAHALLELER = {
    "maslak", "istinye", "ayazağa", "huzur", "poligon",
}

# Beşiktaş neighbourhoods
_BESIKTAS_LUXURY_MAHALLELER = {
    "etiler", "levent", "nisbetiye", "akat", "bebek",
    "arnavutköy", "ulus", "gayrettepe", "levazım",
}
_BESIKTAS_MID_MAHALLELER = {
    "dikilitaş", "türkali", "sinanpaşa", "muradiye", "abbasağa",
    "mecidiye", "ortaköy", "cihannüma",
}

# Üsküdar neighbourhoods
_USKUDAR_LUXURY_MAHALLELER = {
    "çengelköy", "kuzguncuk", "burhaniye", "beylerbeyi",
}
_USKUDAR_MID_MAHALLELER = {
    "sultantepe", "bulgurlu", "bahçelievler", "ferah", "ünalan",
}

# District tiers (fallback when no neighbourhood rule matches)
LUXURY_DISTRICTS = {
    "beşiktaş", "sarıyer", "şişli", "nişantaşı", "teşvikiye",
    "kadıköy", "moda", "caddebostan", "bakırköy", "florya",
    "beyoğlu", "cihangir", "balmumcu",
}

MID_DISTRICTS = {
    "ataşehir", "üsküdar", "kağıthane", "maltepe", "kartal",
    "ümraniye", "başakşehir", "bahçelievler", "küçükçekmece",
    "pendik", "sancaktepe", "çekmeköy", "tuzla", "avcılar",
    "eyüpsultan", "beylikdüzü", "bağcılar", "gaziosmanpaşa",
    "fatih", "zeytinburnu", "güngören",
}

SUBURB_DISTRICTS = {
    "arnavutköy", "silivri", "çatalca", "şile", "sultanbeyli",
    "sultangazi", "esenyurt", "büyükçekmece", "esenler",
    "bayrampaşa",
}


def get_district_tier(konum: str) -> str:
    """Return 'luxury', 'mid', or 'suburb' based on konum.

    Neighbourhood-level rules are checked first so that e.g.
    'Sarıyer / Tarabya Mah.' → 'mid' and 'Sarıyer / Maslak Mah.' → 'luxury'.
    """
    k = konum.lower()

    # --- Neighbourhood-level overrides ---
    # Sarıyer
    if "sarıyer" in k:
        for mah in _SARIYE_LUXURY_MAHALLELER:
            if mah in k:
                return "luxury"
        for mah in _SARIYE_MID_MAHALLELER:
            if mah in k:
                return "mid"
        return "luxury"  # Default for Sarıyer (high-end district)

    # Beşiktaş
    if "beşiktaş" in k:
        for mah in _BESIKTAS_LUXURY_MAHALLELER:
            if mah in k:
                return "luxury"
        for mah in _BESIKTAS_MID_MAHALLELER:
            if mah in k:
                return "mid"
        return "luxury"  # Default for Beşiktaş

    # Üsküdar
    if "üsküdar" in k:
        for mah in _USKUDAR_LUXURY_MAHALLELER:
            if mah in k:
                return "luxury"
        for mah in _USKUDAR_MID_MAHALLELER:
            if mah in k:
                return "mid"
        return "mid"  # Default for Üsküdar

    # --- District-level fallback ---
    for d in LUXURY_DISTRICTS:
        if d in k:
            return "luxury"
    for d in SUBURB_DISTRICTS:
        if d in k:
            return "suburb"
    for d in MID_DISTRICTS:
        if d in k:
            return "mid"
    return "mid"  # default


def extract_room_count(baslik: str) -> str:
    """Extract room info like '2+1', '3+1', '1+0' from title."""
    match = re.search(r"\b(\d+\+\d+)\b", baslik)
    if match:
        return match.group(1)
    return "2+1"


def is_villa_like(baslik: str, oda: str) -> bool:
    """Check if the listing is villa/müstakil/yalı type.

    'dubleks' and 'dublex' are intentionally excluded — most duplex apartments
    are priced like regular apartments, not villas.
    """
    b = baslik.lower()
    # Word-boundary-aware checks
    for keyword in ["villa", "müstakil", "tripleks", "köşk", "fourlex"]:
        if re.search(r"\b" + re.escape(keyword) + r"\b", b):
            return True
    # 'yalı' needs special handling: must be standalone word, not inside 'eşyalı'
    if re.search(r"(?<![a-zçğıöşüa-z])yalı\b", b):
        return True
    return False


def _gauss_int(mean: float, lo: int, hi: int) -> int:
    """Return a Gaussian-sampled integer clamped to [lo, hi].

    Uses the 3-sigma rule: std = (hi - lo) / 6, so ~99.7 % of samples
    fall within [lo, hi] before clamping.
    """
    std = (hi - lo) / 6.0
    val = int(random.gauss(mean, std))
    return max(lo, min(hi, val))


def simulate_metrekare(baslik: str, oda: str) -> str:
    """Simulate m2 based on room count and title hints."""
    # Check title for explicit m² value (2-4 digits before m² or M2).
    # Skip if this appears to be a balcony/garden/terrace/veranda area.
    for m in re.finditer(r"(\d{2,4})\s*m[²2]", baslik, re.IGNORECASE):
        val = int(m.group(1))
        after = baslik[m.end():].lower().strip()
        if re.match(r"[\s,]*(balkon|bahçe|teras|veranda)", after):
            continue
        # Reasonable apartment/house range: 20–2000 m²
        if 20 <= val <= 2000:
            return str(val)

    if is_villa_like(baslik, oda):
        mean, lo, hi = 350, 250, 500
        return str(_gauss_int(mean, lo, hi))

    ranges = {
        "1+0": (35, 25, 45),
        "1+1": (58, 45, 75),
        "2+1": (88, 70, 110),
        "3+1": (120, 100, 145),
        "4+1": (165, 140, 200),
        "4+2": (220, 180, 280),
        "5+1": (220, 180, 280),
        "5+2": (220, 180, 280),
    }
    mean, lo, hi = ranges.get(oda, (220, 180, 280))
    # For large room counts not in map
    first = oda.split("+")[0] if "+" in oda else "2"
    try:
        n = int(first)
    except ValueError:
        n = 2
    if n >= 6:
        mean, lo, hi = 350, 250, 500
    return str(_gauss_int(mean, lo, hi))


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
    # Check title for explicit price — only accept well-formed patterns
    # e.g. "35.000 TL", "50 000 Tl", "35000TL", "150000 tl"
    price_match = re.search(
        r"\b(\d{2,3}[\.\s]?\d{3})\s*[Tt][Ll]\b"
        r"|\b(\d{5,6})\s*[Tt][Ll]\b",
        baslik,
    )
    if price_match:
        raw = (price_match.group(1) or price_match.group(2))
        raw = raw.replace(".", "").replace(" ", "")
        try:
            return str(int(raw))
        except ValueError:
            pass

    villa = is_villa_like(baslik, oda)

    # Price table: (mean, lo, hi) per tier and room type
    # 2025 Q1 Istanbul rental market
    PRICES = {
        "luxury": {
            "villa":  (400000, 200000, 800000),
            "1+0":    (35000,  22000,  55000),
            "1+1":    (55000,  35000,  90000),
            "2+1":    (85000,  55000, 140000),
            "3+1":    (130000, 85000, 200000),
            "4+1":    (200000, 130000, 350000),
            "4+2":    (280000, 180000, 500000),
            "other":  (280000, 180000, 500000),
        },
        "mid": {
            "villa":  (200000, 130000, 350000),
            "1+0":    (20000,  14000,  30000),
            "1+1":    (32000,  20000,  50000),
            "2+1":    (50000,  32000,  75000),
            "3+1":    (75000,  50000, 110000),
            "4+1":    (110000, 75000, 160000),
            "4+2":    (150000, 100000, 220000),
            "other":  (150000, 100000, 220000),
        },
        "suburb": {
            "villa":  (130000, 90000, 200000),
            "1+0":    (14000,  10000,  20000),
            "1+1":    (22000,  15000,  32000),
            "2+1":    (35000,  24000,  50000),
            "3+1":    (52000,  36000,  72000),
            "4+1":    (75000,  52000, 105000),
            "4+2":    (100000, 70000, 140000),
            "other":  (100000, 70000, 140000),
        },
    }

    tier_prices = PRICES.get(tier, PRICES["mid"])

    if villa:
        mean, lo, hi = tier_prices["villa"]
    else:
        # Normalise oda: treat 5+1, 5+2, 6+… etc. as "other" (≥ 4+2 bucket)
        first = oda.split("+")[0] if "+" in oda else "2"
        try:
            n = int(first)
        except ValueError:
            n = 2
        second = oda.split("+")[1] if "+" in oda else "1"
        try:
            s = int(second)
        except ValueError:
            s = 1

        if n >= 5 or (n == 4 and s >= 2):
            key = "4+2"
        elif oda in tier_prices:
            key = oda
        else:
            key = "other"
        mean, lo, hi = tier_prices.get(key, tier_prices["other"])

    val = _gauss_int(mean, lo, hi)
    # Round to nearest 500
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
