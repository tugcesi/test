#!/usr/bin/env python3
"""
Simulate missing values for istanbul_kiralik_complete.csv
and produce istanbul_kiralik_simulated.csv

Pricing model: mahalle-level TL/m² rates derived from
Endeksa.com 2025 Q1 Istanbul rental data (recalibrated).
"""

import csv
import random
import re

INPUT_FILE  = "istanbul_kiralik_complete.csv"
OUTPUT_FILE = "istanbul_kiralik_simulated.csv"

# ──────────────────────────────────────────────────────────────────────────────
# SEGMENT > İLÇE > MAHALLE  →  m2_fiyat (TL/m²/ay) + std
# Kaynak: Endeksa.com 2025 Q1 – kalibre edilmiş değerler
# Not: fiyat = m2 * m2_fiyat + gauss(0, std * m2**0.5)
# Örnek kontrol: Kadıköy/Moda 65m²  → ~16.900 TL ✓
#                Beşiktaş 91m²       → ~17.000 TL ✓
#                Ümraniye 96m²       → ~9.100 TL  ✓
#                Esenyurt 90m²       → ~4.050 TL  ✓
# ──────────────────────────────────────────────────────────────────────────────
MAHALLELER: dict[str, dict] = {

    # ── AVRUPA YAKASI ──────────────────────────────────────────────────────────

    "Üst Segment – Boğaz (Avrupa)": {
        "Beşiktaş": {
            "Bebek":              {"m2_fiyat": 295, "std": 56},
            "Etiler":             {"m2_fiyat": 260, "std": 52},
            "Levent":             {"m2_fiyat": 220, "std": 43},
            "Arnavutköy":         {"m2_fiyat": 245, "std": 49},
            "Ortaköy":            {"m2_fiyat": 210, "std": 43},
            "Balmumcu":           {"m2_fiyat": 185, "std": 37},
        },
        "Sarıyer": {
            "Yeniköy":            {"m2_fiyat": 280, "std": 53},
            "Tarabya":            {"m2_fiyat": 245, "std": 49},
            "İstinye":            {"m2_fiyat": 220, "std": 43},
            "Zekeriyaköy":        {"m2_fiyat": 170, "std": 34},
            "Maslak":             {"m2_fiyat": 160, "std": 32},
            "Rumelifeneri":       {"m2_fiyat": 135, "std": 27},
        },
    },

    "Üst-Orta Segment – Merkez Avrupa": {
        "Şişli": {
            "Nişantaşı":          {"m2_fiyat": 235, "std": 47},
            "Teşvikiye":          {"m2_fiyat": 215, "std": 43},
            "Bomonti":            {"m2_fiyat": 160, "std": 32},
            "Fulya":              {"m2_fiyat": 150, "std": 30},
            "Mecidiyeköy":        {"m2_fiyat": 130, "std": 26},
            "Şişli Merkez":       {"m2_fiyat": 110, "std": 22},
        },
        "Beyoğlu": {
            "Cihangir":           {"m2_fiyat": 195, "std": 39},
            "Galata":             {"m2_fiyat": 180, "std": 36},
            "Karaköy":            {"m2_fiyat": 160, "std": 32},
            "Taksim":             {"m2_fiyat": 150, "std": 30},
            "Çukurcuma":          {"m2_fiyat": 165, "std": 33},
            "Tarlabaşı":          {"m2_fiyat": 90,  "std": 18},
        },
        "Kağıthane": {
            "Çağlayan":           {"m2_fiyat": 110, "std": 22},
            "Gültepe":            {"m2_fiyat": 90,  "std": 18},
            "Hamidiye":           {"m2_fiyat": 85,  "std": 17},
            "Seyrantepe":         {"m2_fiyat": 100, "std": 20},
        },
    },

    "Orta Segment – Tarihi Yarımada": {
        "Fatih": {
            "Balat":              {"m2_fiyat": 120, "std": 24},
            "Fener":              {"m2_fiyat": 110, "std": 22},
            "Samatya":            {"m2_fiyat": 90,  "std": 18},
            "Sultanahmet":        {"m2_fiyat": 125, "std": 25},
            "Aksaray":            {"m2_fiyat": 80,  "std": 16},
            "Fatih Merkez":       {"m2_fiyat": 85,  "std": 17},
        },
        "Eyüpsultan": {
            "Eyüp Merkez":        {"m2_fiyat": 80,  "std": 16},
            "Alibeyköy":          {"m2_fiyat": 70,  "std": 14},
            "Rami":               {"m2_fiyat": 65,  "std": 13},
        },
    },

    "Orta Segment – Güney Avrupa": {
        "Bakırköy": {
            "Ataköy 1-4":         {"m2_fiyat": 150, "std": 30},
            "Ataköy 5-11":        {"m2_fiyat": 140, "std": 28},
            "Yeşilköy":           {"m2_fiyat": 130, "std": 26},
            "Florya":             {"m2_fiyat": 125, "std": 25},
            "Bakırköy Merkez":    {"m2_fiyat": 120, "std": 24},
        },
        "Zeytinburnu": {
            "Yeşiltepe":          {"m2_fiyat": 90,  "std": 18},
            "Seyitnizam":         {"m2_fiyat": 80,  "std": 16},
            "Veliefendi":         {"m2_fiyat": 80,  "std": 16},
            "Merkezefendi":       {"m2_fiyat": 80,  "std": 16},
        },
        "Bahçelievler": {
            "Şirinevler":         {"m2_fiyat": 80,  "std": 16},
            "Yenibosna":          {"m2_fiyat": 80,  "std": 16},
            "Bahçelievler Mrk.":  {"m2_fiyat": 80,  "std": 16},
        },
    },

    "Alt-Orta Segment – Batı Avrupa": {
        "Bağcılar": {
            "Kirazlı":            {"m2_fiyat": 65,  "std": 13},
            "Bağcılar Merkez":    {"m2_fiyat": 65,  "std": 13},
            "Güneşli":            {"m2_fiyat": 75,  "std": 15},
            "Mahmutbey":          {"m2_fiyat": 70,  "std": 14},
        },
        "Avcılar": {
            "Avcılar Merkez":     {"m2_fiyat": 80,  "std": 16},
            "Ambarlı":            {"m2_fiyat": 65,  "std": 13},
            "Firuzköy":           {"m2_fiyat": 65,  "std": 13},
        },
        "Beylikdüzü": {
            "Gürpınar":           {"m2_fiyat": 75,  "std": 15},
            "Büyükşehir":         {"m2_fiyat": 80,  "std": 16},
            "Adnan Kahveci":      {"m2_fiyat": 70,  "std": 14},
        },
        "Esenyurt": {
            "Esenyurt Merkez":    {"m2_fiyat": 50,  "std": 10},
            "Fatih Mah.(Esen)":   {"m2_fiyat": 45,  "std": 9},
            "Pınar":              {"m2_fiyat": 45,  "std": 9},
            "Saadetdere":         {"m2_fiyat": 40,  "std": 8},
        },
    },

    # ── ANADOLU YAKASI ─────────────────────────────────────────────────────────

    "Üst Segment – Boğaz (Anadolu)": {
        "Üsküdar": {
            "Çengelköy":          {"m2_fiyat": 210, "std": 43},
            "Kuzguncuk":          {"m2_fiyat": 195, "std": 39},
            "Beylerbeyi":         {"m2_fiyat": 170, "std": 34},
            "Üsküdar Merkez":     {"m2_fiyat": 135, "std": 27},
            "Bağlarbaşı":         {"m2_fiyat": 125, "std": 25},
            "Acıbadem(Üsk)":      {"m2_fiyat": 140, "std": 28},
        },
        "Beykoz": {
            "Anadoluhisarı":      {"m2_fiyat": 170, "std": 34},
            "Kavacık":            {"m2_fiyat": 135, "std": 27},
            "Paşabahçe":          {"m2_fiyat": 110, "std": 22},
            "Beykoz Merkez":      {"m2_fiyat": 100, "std": 20},
        },
    },

    "Üst-Orta Segment – Anadolu Merkez": {
        "Kadıköy": {
            "Moda":               {"m2_fiyat": 260, "std": 52},
            "Bağdat Caddesi":     {"m2_fiyat": 235, "std": 47},
            "Fenerbahçe":         {"m2_fiyat": 210, "std": 43},
            "Erenköy":            {"m2_fiyat": 175, "std": 35},
            "Acıbadem(Kad)":      {"m2_fiyat": 160, "std": 32},
            "Göztepe":            {"m2_fiyat": 150, "std": 30},
            "Kozyatağı":          {"m2_fiyat": 140, "std": 28},
            "Kadıköy Merkez":     {"m2_fiyat": 130, "std": 26},
        },
        "Ataşehir": {
            "Ataşehir Merkez":    {"m2_fiyat": 130, "std": 26},
            "İçerenköy":          {"m2_fiyat": 140, "std": 28},
            "Küçükbakkalköy":     {"m2_fiyat": 125, "std": 25},
            "Kayışdağı":          {"m2_fiyat": 110, "std": 22},
            "Barbaros":           {"m2_fiyat": 125, "std": 25},
        },
    },

    "Orta Segment – Anadolu Orta Kuşak": {
        "Maltepe": {
            "Cevizli":            {"m2_fiyat": 105, "std": 21},
            "Bağlarbaşı(Mal)":    {"m2_fiyat": 100, "std": 20},
            "Maltepe Merkez":     {"m2_fiyat": 95,  "std": 19},
            "Altayçeşme":         {"m2_fiyat": 85,  "std": 17},
        },
        "Kartal": {
            "Kordonboyu":         {"m2_fiyat": 95,  "std": 19},
            "Yakacık":            {"m2_fiyat": 85,  "std": 17},
            "Kartal Merkez":      {"m2_fiyat": 80,  "std": 16},
            "Uğur Mumcu":         {"m2_fiyat": 80,  "std": 16},
        },
        "Ümraniye": {
            "Site":               {"m2_fiyat": 100, "std": 20},
            "Ümraniye Merkez":    {"m2_fiyat": 95,  "std": 19},
            "Dudullu":            {"m2_fiyat": 85,  "std": 17},
            "Çakmak":             {"m2_fiyat": 80,  "std": 16},
            "Namık Kemal":        {"m2_fiyat": 90,  "std": 18},
        },
    },

    "Alt-Orta Segment – Anadolu Dış Kuşak": {
        "Pendik": {
            "Yenişehir":          {"m2_fiyat": 80,  "std": 16},
            "Kaynarca":           {"m2_fiyat": 70,  "std": 14},
            "Pendik Merkez":      {"m2_fiyat": 70,  "std": 14},
            "Kurtköy":            {"m2_fiyat": 65,  "std": 13},
        },
        "Tuzla": {
            "İçmeler":            {"m2_fiyat": 80,  "std": 16},
            "Aydınlı":            {"m2_fiyat": 70,  "std": 14},
            "Tuzla Merkez":       {"m2_fiyat": 65,  "std": 13},
        },
        "Sultanbeyli": {
            "Sultanbeyli Mrk.":   {"m2_fiyat": 50,  "std": 10},
            "Hasanpaşa(Sul)":     {"m2_fiyat": 45,  "std": 9},
            "Mehmet Akif":        {"m2_fiyat": 40,  "std": 8},
        },
        "Sancaktepe": {
            "Sancaktepe Mrk.":    {"m2_fiyat": 55,  "std": 11},
            "Samandıra":          {"m2_fiyat": 60,  "std": 12},
            "Yenidoğan(San)":     {"m2_fiyat": 50,  "std": 10},
        },
    },
}

# ── Tier fallback (mahalle bulunamazsa segment adından türetilir) ─────────────
TIER_FALLBACK = {
    "üst":      {"m2_fiyat": 185, "std": 37},
    "üst-orta": {"m2_fiyat": 120, "std": 24},
    "orta":     {"m2_fiyat": 85,  "std": 17},
    "alt-orta": {"m2_fiyat": 55,  "std": 11},
    "alt":      {"m2_fiyat": 35,  "std": 7},
}

# ── Oda → m² aralıkları ───────────────────────────────────────────────────────
ODA_M2 = {
    "1+0": (25,  50),
    "1+1": (45,  80),
    "2+1": (70, 120),
    "2+2": (80, 130),
    "3+1": (100, 180),
    "4+1": (140, 250),
    "4+2": (170, 280),
    "5+1": (180, 350),
    "5+2": (200, 380),
    "6+1": (250, 500),
}


# ──────────────────────────────────────────────────────────────────────────────
# Yardımcı fonksiyonlar
# ──────────────────────────────────────────────────────────────────────────────

def is_empty(val) -> bool:
    """Return True if val is None, empty string, or the literal string 'nan'/'NaN'."""
    if val is None:
        return True
    s = str(val).strip()
    return s == "" or s.lower() == "nan"


def lookup_mahalle(konum: str) -> tuple[dict | None, str]:
    """
    Konum string'inden mahalle düzeyinde fiyat verisi arar.
    Returns (fiyat_dict, segment_adi) — bulunamazsa (None, "").
    Longest-match kullanır.
    """
    kl = konum.lower()
    best_data = None
    best_segment = ""
    best_len = 0

    for segment, ilceler in MAHALLELER.items():
        for ilce, mahalleler in ilceler.items():
            for mahalle, data in mahalleler.items():
                key = mahalle.lower()
                if key in kl and len(key) > best_len:
                    best_data = data
                    best_segment = segment
                    best_len = len(key)

    return best_data, best_segment


def get_tier(konum: str) -> str:
    """
    Konum'dan segment adını bulup tier döndürür.
    Mahalle eşleşmesi yoksa ilçe adına göre tahmin eder.
    """
    _, segment = lookup_mahalle(konum)
    if segment:
        sl = segment.lower()
        if sl.startswith("üst segment"):
            return "üst"
        if sl.startswith("üst-orta"):
            return "üst-orta"
        if sl.startswith("orta"):
            return "orta"
        if sl.startswith("alt-orta"):
            return "alt-orta"
        return "alt"

    # Fallback: ilçe adına göre kaba tahmin
    kl = konum.lower()
    luxury = {"beşiktaş", "sarıyer", "kadıköy", "şişli", "beyoğlu", "bakırköy", "üsküdar"}
    suburb = {"esenyurt", "sultanbeyli", "sancaktepe", "arnavutköy", "silivri",
              "çatalca", "şile", "sultangazi", "esenler", "büyükçekmece"}
    for d in luxury:
        if d in kl:
            return "üst-orta"
    for d in suburb:
        if d in kl:
            return "alt-orta"
    return "orta"


def extract_room_count(baslik: str) -> str:
    match = re.search(r"\b(\d+\+\d+)\b", baslik)
    return match.group(1) if match else "2+1"


def is_villa_like(baslik: str) -> bool:
    b = baslik.lower()
    for kw in ["villa", "müstakil", "tripleks", "dublex", "dubleks"]:
        if re.search(r"\b" + re.escape(kw) + r"\b", b):
            return True
    if re.search(r"(?<![a-zçğışöüa-z])yalı\b", b):
        return True
    return False


def simulate_metrekare(baslik: str, oda: str) -> str:
    # 1. Başlıkta açık m² değeri var mı?
    for m in re.finditer(r"(\d{2,4})\s*m[²2]", baslik, re.IGNORECASE):
        val = int(m.group(1))
        after = baslik[m.end():].lower().strip()
        if re.match(r"[\s,]*balkon", after):
            continue
        if 20 <= val <= 2000:
            return str(val)

    # 2. Villa/müstakil
    if is_villa_like(baslik):
        return str(random.randint(200, 500))

    # 3. Oda sayısına göre aralık (triangular dağılım)
    lo, hi = ODA_M2.get(oda, (120, 200))
    first = oda.split("+")[0] if "+" in oda else "2"
    try:
        n = int(first)
    except ValueError:
        n = 2
    if n >= 6:
        lo, hi = 250, 500
    return str(int(random.triangular(lo, hi, lo + (hi - lo) * 0.45)))


def simulate_kat(baslik: str) -> str:
    b = baslik.lower()
    m = re.search(r"(\d+)[./](\d+)[\s.]*kat", b)
    if m:
        return m.group(2)
    m = re.search(r"(\d+)\s*\.?(\d*)kat\b", b)
    if m:
        return m.group(1)
    if "zemin" in b:
        return "0"
    if "giriş" in b:
        return str(random.choice([0, 1]))
    if "çatı" in b:
        return str(random.randint(10, 14))
    if any(k in b for k in ["teras", "teraslı"]):
        return str(random.randint(8, 14))
    if any(k in b for k in ["dubleks", "dublex", "tripleks"]):
        return str(random.randint(3, 10))
    if "yüksek" in b:
        return str(random.randint(6, 14))
    return str(random.randint(1, 12))


def simulate_fiyat(baslik: str, oda: str, konum: str) -> str:
    # 1. Başlıkta açık fiyat var mı?
    price_match = re.search(r"(\d[\d\.\s]{2,})\s*[Tt][Ll]", baslik)
    if price_match:
        raw = price_match.group(1).replace(".", "").replace(" ", "")
        try:
            val = int(raw)
            if 5_000 <= val <= 5_000_000:
                return str(val)
        except ValueError:
            pass

    # 2. Mahalle düzeyinde m² bazlı fiyatlandırma
    mahalle_data, segment = lookup_mahalle(konum)
    tier = get_tier(konum)

    if mahalle_data:
        m2_birim = mahalle_data["m2_fiyat"]
        std = mahalle_data["std"]
    else:
        fb = TIER_FALLBACK.get(tier, TIER_FALLBACK["orta"])
        m2_birim = fb["m2_fiyat"]
        std = fb["std"]

    villa = is_villa_like(baslik)
    if villa:
        m2_birim = int(m2_birim * 1.4)
        std = int(std * 1.4)

    lo_m2, hi_m2 = ODA_M2.get(oda, (120, 200))
    m2 = random.randint(lo_m2, hi_m2)

    # Scaled noise: proportional to sqrt(m2) for realistic spread
    noise = random.gauss(0, std * (m2 ** 0.5))
    fiyat = int(m2 * m2_birim + noise)
    fiyat = max(5000, fiyat)
    fiyat = round(fiyat / 500) * 500
    return str(fiyat)


def simulate_yapi_yasi(baslik: str) -> str:
    b = baslik.lower()
    if any(k in b for k in ["sıfır", "yeni bina", "yeni yapı", "2024", "2025", "2026"]):
        return str(random.choice([0, 1]))
    m = re.search(r"(\d+)\s*yıllık", b)
    if m:
        return m.group(1)
    m = re.search(r"\b(19\d{2}|20[0-2]\d)\b", b)
    if m:
        yil = int(m.group(1))
        return str(max(0, 2025 - yil))
    return str(random.randint(0, 25))


def simulate_esya(baslik: str) -> str:
    b = baslik.lower()
    if any(k in b for k in ["eşyalı", "mobilyalı", "full eşya", "full mobilya", "eşyali"]):
        return "Eşyalı"
    if any(k in b for k in ["eşyasız", "boş daire", "boş ev"]):
        return "Eşyasız"
    return "Eşyalı" if random.random() < 0.40 else "Eşyasız"


def simulate_isitma(baslik: str, tier: str) -> str:
    b = baslik.lower()
    if any(k in b for k in ["kombili", "kombi"]):
        return "Kombi"
    if any(k in b for k in ["merkezi ısıtma", "merkezi sistem", "merkezi"]):
        return "Merkezi"
    if "yerden ısıtma" in b:
        return "Yerden Isıtma"
    if "klima" in b:
        return "Klima (Split)"

    if tier in ("üst", "üst-orta"):
        choices = ["Kombi", "Merkezi", "Yerden Isıtma", "Klima (Split)"]
        weights = [45, 35, 12, 8]
    elif tier in ("alt-orta", "alt"):
        choices = ["Kombi", "Soba/Doğalgaz", "Merkezi", "Klima (Split)"]
        weights = [60, 20, 12, 8]
    else:
        choices = ["Kombi", "Merkezi", "Soba/Doğalgaz", "Klima (Split)"]
        weights = [55, 30, 8, 7]

    total = sum(weights)
    r = random.randint(1, total)
    cumulative = 0
    for choice, w in zip(choices, weights):
        cumulative += w
        if r <= cumulative:
            return choice
    return choices[0]

# ──────────────────────────────────────────────────────────────────────────────
def process_row(row: dict, index: int) -> dict:
    """Fill missing values in a row using simulation rules."""
    random.seed(index)

    baslik = row.get("Başlık", "") or ""
    konum  = row.get("Konum",  "") or ""
    tier   = get_tier(konum)

    # Oda Sayısı
    oda = row.get("Oda Sayısı", "")
    if is_empty(oda):
        oda = extract_room_count(baslik)
        row["Oda Sayısı"] = oda
    else:
        oda = str(oda).strip()

    # Metrekare
    if is_empty(row.get("Metrekare")):
        row["Metrekare"] = simulate_metrekare(baslik, oda)

    # Kat
    if is_empty(row.get("Kat")):
        row["Kat"] = simulate_kat(baslik)

    # Fiyat
    if is_empty(row.get("Fiyat")):
        row["Fiyat"] = simulate_fiyat(baslik, oda, konum)

    # Yapı Yaşı
    if is_empty(row.get("Yapı Yaşı")):
        row["Yapı Yaşı"] = simulate_yapi_yasi(baslik)

    # Eşya
    if is_empty(row.get("Eşya")):
        row["Eşya"] = simulate_esya(baslik)

    # Isıtma
    if is_empty(row.get("Isıtma")):
        row["Isıtma"] = simulate_isitma(baslik, tier)

    return row


def main():
    with open(INPUT_FILE, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    processed = [process_row(row, i) for i, row in enumerate(rows)]

    with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processed)

    print(f"Done. {len(processed)} rows written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()