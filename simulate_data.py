#!/usr/bin/env python3
"""
Simulate missing values for istanbul_kiralik_complete.csv
and produce istanbul_kiralik_simulated.csv

Pricing model: mahalle-level TL/m² rates derived from
Endeksa.com 2025 Q1 Istanbul rental data + generate_istanbul_dataset.py.
"""

import csv
import random
import re

INPUT_FILE  = "istanbul_kiralik_complete.csv"
OUTPUT_FILE = "istanbul_kiralik_simulated.csv"

# ─────────────────────────────────────────────────────────────────────────────
# BÖLGE > İLÇE > MAHALLE  →  m2_fiyat (TL/ay) + std
# Kaynak: Endeksa.com 2025 Q1 & generate_istanbul_dataset.py
# ─────────────────────────────────────────────────────────────────────────────
MAHALLE_FIYAT: dict[str, dict] = {
    # ── Beşiktaş ──────────────────────────────────────────────────────────
    "bebek":            {"m2": 3200, "std": 600},
    "etiler":           {"m2": 2800, "std": 500},
    "levent":           {"m2": 2400, "std": 450},
    "arnavutköy mah":   {"m2": 2600, "std": 500},   # Beşiktaş mahallesi
    "ortaköy":          {"m2": 2200, "std": 420},
    "balmumcu":         {"m2": 1900, "std": 380},
    "dikilitaş":        {"m2": 2000, "std": 400},
    "gayrettepe":       {"m2": 2000, "std": 390},
    "nisbetiye":        {"m2": 2300, "std": 440},
    "akatlar":          {"m2": 2100, "std": 410},
    "akat":             {"m2": 2100, "std": 410},
    "levazım":          {"m2": 2200, "std": 430},
    "abbasağa":         {"m2": 2400, "std": 460},
    "cihannüma":        {"m2": 2200, "std": 430},
    "vişnezade":        {"m2": 2300, "std": 440},
    "sinanpaşa":        {"m2": 2100, "std": 410},
    "türkali":          {"m2": 2000, "std": 400},
    "muradiye":         {"m2": 2000, "std": 400},
    "ulus mah":         {"m2": 2500, "std": 480},
    # ── Sarıyer ───────────────────────────────────────────────────────────
    "yeniköy":          {"m2": 3000, "std": 580},
    "tarabya":          {"m2": 2700, "std": 520},
    "ferahevler":       {"m2": 2400, "std": 460},
    "istinye":          {"m2": 2400, "std": 460},
    "poligon":          {"m2": 2200, "std": 430},
    "zekeriyaköy":      {"m2": 1800, "std": 350},
    "maslak":           {"m2": 1600, "std": 320},
    "ayazağa":          {"m2": 1400, "std": 280},
    "rumeli":           {"m2": 1400, "std": 280},
    "göktürk":          {"m2": 1600, "std": 320},
    "çamlıtepe":        {"m2": 1300, "std": 260},
    "cumhuriyet mah sarıyer": {"m2": 1200, "std": 250},
    # ── Şişli ─────────────────────────────────────────────────────────────
    "nişantaşı":        {"m2": 2500, "std": 480},
    "teşvikiye":        {"m2": 2300, "std": 450},
    "harbiye":          {"m2": 2100, "std": 410},
    "meşrutiyet":       {"m2": 1700, "std": 340},
    "bomonti":          {"m2": 1600, "std": 320},
    "fulya":            {"m2": 1500, "std": 300},
    "mecidiyeköy":      {"m2": 1300, "std": 260},
    "esentepe":         {"m2": 1400, "std": 280},
    "merkez mah şişli": {"m2": 1100, "std": 220},
    "19 mayıs":         {"m2": 1200, "std": 240},
    "ergenekon":        {"m2": 1100, "std": 220},
    "bozkurt":          {"m2": 1000, "std": 210},
    "feriköy":          {"m2": 1200, "std": 240},
    "paşa mah":         {"m2": 1100, "std": 220},
    "gülbahar":         {"m2": 1100, "std": 220},
    "halide edip":      {"m2": 1100, "std": 220},
    "kuştepe":          {"m2": 1000, "std": 210},
    "yayla mah":        {"m2": 950,  "std": 200},
    "eskişehir mah":    {"m2": 1100, "std": 220},
    "inönü mah şişli":  {"m2": 1700, "std": 340},
    "izzet paşa":       {"m2": 1100, "std": 220},
    # ── Beyoğlu ───────────────────────────────────────────────────────────
    "cihangir":         {"m2": 2000, "std": 400},
    "galata":           {"m2": 1800, "std": 360},
    "karaköy":          {"m2": 1600, "std": 320},
    "taksim":           {"m2": 1500, "std": 300},
    "firuzağa":         {"m2": 1800, "std": 360},
    "çukurcuma":        {"m2": 1700, "std": 340},
    "tarlabaşı":        {"m2": 900,  "std": 200},
    "hacıahmet":        {"m2": 1400, "std": 280},
    "kalyoncu":         {"m2": 1200, "std": 250},
    "bostan mah":       {"m2": 1100, "std": 230},
    "kuloğlu":          {"m2": 1500, "std": 300},
    "kulaksız":         {"m2": 900,  "std": 190},
    "gümüşsuyu":        {"m2": 1700, "std": 340},
    "ömer avni":        {"m2": 1700, "std": 340},
    "kaptanpaşa":       {"m2": 1000, "std": 210},
    "örnektepe":        {"m2": 800,  "std": 175},
    "tomtom":           {"m2": 1800, "std": 360},
    "istiklal mah":     {"m2": 1500, "std": 300},
    "katip mustafa":    {"m2": 1400, "std": 280},
    "camiikebir":       {"m2": 900,  "std": 190},
    "pürtelaş":         {"m2": 1500, "std": 300},
    # ── Kağıthane ─────────────────────────────────────────────────────────
    "çağlayan":         {"m2": 1100, "std": 220},
    "gültepe":          {"m2": 900,  "std": 190},
    "hamidiye":         {"m2": 850,  "std": 180},
    "seyrantepe":       {"m2": 950,  "std": 200},
    "merkez mah kağıthane": {"m2": 1000, "std": 210},
    "ortabayır":        {"m2": 1000, "std": 210},
    "emniyet evleri":   {"m2": 1100, "std": 220},
    "telsizler":        {"m2": 850,  "std": 180},
    "yeşilce":          {"m2": 900,  "std": 190},
    "şirintepe":        {"m2": 850,  "std": 180},
    "harmantepe":       {"m2": 900,  "std": 190},
    "sultan selim":     {"m2": 900,  "std": 190},
    "yahya kemal":      {"m2": 1000, "std": 210},
    "mehmet akif ersoy kağıthane": {"m2": 850, "std": 180},
    "çeliktepe":        {"m2": 800,  "std": 175},
    # ── Fatih ─────────────────────────────────────────────────────────────
    "balat":            {"m2": 1200, "std": 250},
    "fener":            {"m2": 1100, "std": 230},
    "samatya":          {"m2": 900,  "std": 190},
    "sultanahmet":      {"m2": 1300, "std": 260},
    "aksaray":          {"m2": 780,  "std": 170},
    "molla gürani":     {"m2": 800,  "std": 175},
    "mevlanakapı":      {"m2": 800,  "std": 175},
    "şehremini":        {"m2": 780,  "std": 170},
    "yedikule":         {"m2": 800,  "std": 175},
    "silivrikapı":      {"m2": 750,  "std": 165},
    "cerrahpaşa":       {"m2": 800,  "std": 175},
    "haseki sultan":    {"m2": 820,  "std": 178},
    "seyyid ömer":      {"m2": 800,  "std": 175},
    "koca mustafapaşa": {"m2": 750,  "std": 165},
    "sümbül efendi":    {"m2": 750,  "std": 165},
    "iskenderpaşa":     {"m2": 780,  "std": 170},
    # ── Eyüpsultan ────────────────────────────────────────────────────────
    "göktürk merkez":   {"m2": 1600, "std": 320},
    "mimar sinan eyüp": {"m2": 800,  "std": 175},
    "alibeyköy":        {"m2": 620,  "std": 145},
    "güzeltepe":        {"m2": 700,  "std": 158},
    "esentepe eyüp":    {"m2": 700,  "std": 158},
    "5. levent":        {"m2": 1200, "std": 250},
    "silahtarağa":      {"m2": 700,  "std": 158},
    "topçular":         {"m2": 650,  "std": 148},
    "mithatpaşa":       {"m2": 750,  "std": 165},
    # ── Bakırköy ──────────────────────────────────────────────────────────
    "ataköy":           {"m2": 1400, "std": 280},
    "yeşilköy":         {"m2": 1250, "std": 260},
    "florya":           {"m2": 1150, "std": 240},
    "şenlikköy":        {"m2": 1150, "std": 240},
    "basınköy":         {"m2": 1200, "std": 250},
    "kartaltepe":       {"m2": 1000, "std": 210},
    "bakırköy merkez":  {"m2": 1100, "std": 225},
    # ── Zeytinburnu ───────────────────────────────────────────────────────
    "veliefendi":       {"m2": 780,  "std": 170},
    "merkezefendi":     {"m2": 750,  "std": 165},
    "kazlıçeşme":       {"m2": 850,  "std": 185},
    # ── Bahçelievler ──────────────────────────────────────────────────────
    "yenibosna":        {"m2": 750,  "std": 165},
    "bahçelievler mah": {"m2": 780,  "std": 170},
    "siyavuşpaşa":      {"m2": 720,  "std": 160},
    "soğanlı":          {"m2": 700,  "std": 158},
    "hürriyet mah bahç":{"m2": 700,  "std": 158},
    # ── Bağcılar ──────────────────────────────────────────────────────────
    "bağcılar":         {"m2": 640,  "std": 148},
    "yenimahalle bağ":  {"m2": 600,  "std": 138},
    "15 temmuz":        {"m2": 650,  "std": 150},
    # ── Avcılar ───────────────────────────────────────────────────────────
    "cihangir mah avcı":{"m2": 700,  "std": 158},
    "denizköşkler":     {"m2": 680,  "std": 154},
    "tahtakale":        {"m2": 700,  "std": 158},
    # ── Beylikdüzü ────────────────────────────────────────────────────────
    "gürpınar":         {"m2": 720,  "std": 160},
    "büyükşehir":       {"m2": 750,  "std": 168},
    "adnan kahveci":    {"m2": 690,  "std": 155},
    "kavaklı":          {"m2": 700,  "std": 158},
    "yakuplu":          {"m2": 720,  "std": 162},
    "marmara mah":      {"m2": 750,  "std": 168},
    "cumhuriyet mah bey":{"m2": 700, "std": 158},
    "dereağzı":         {"m2": 680,  "std": 154},
    # ── Esenyurt ──────────────────────────────────────────────────────────
    "yeşilkent":        {"m2": 500,  "std": 115},
    "zafer mah":        {"m2": 480,  "std": 110},
    "barbaros hayrettin":{"m2": 500, "std": 115},
    "piri reis":        {"m2": 480,  "std": 110},
    "necip fazıl":      {"m2": 460,  "std": 105},
    "esenyurt merkez":  {"m2": 480,  "std": 110},
    "orhan gazi":       {"m2": 460,  "std": 105},
    "koza mah":         {"m2": 500,  "std": 115},
    "üçevler":          {"m2": 480,  "std": 110},
    "pınar mah":        {"m2": 460,  "std": 105},
    "güzelyurt":        {"m2": 480,  "std": 110},
    "hürriyet mah esen":{"m2": 460,  "std": 105},
    "mevlana mah esen": {"m2": 480,  "std": 110},
    "cumhuriyet mah esen":{"m2": 480,"std": 110},
    "mehmet akif ersoy esen":{"m2": 460,"std": 105},
    "istiklal mah esen":{"m2": 460,  "std": 105},
    # ── Arnavutköy (ilçe) ─────────────────────────────────────────────────
    "hadımköy":         {"m2": 600,  "std": 138},
    "mavigöl":          {"m2": 650,  "std": 148},
    "deliklikaya":      {"m2": 600,  "std": 138},
    "hicret":           {"m2": 600,  "std": 138},
    # ── Büyükçekmece ──────────────────────────────────────────────────────
    "mimaroba":         {"m2": 650,  "std": 150},
    "pınartepe":        {"m2": 620,  "std": 142},
    "türkoba":          {"m2": 600,  "std": 138},
    "sinanoba":         {"m2": 620,  "std": 142},
    # ── Gaziosmanpaşa ─────────────────────────────────────────────────────
    "merkez mah gaz":   {"m2": 700,  "std": 158},
    "mevlana mah gaz":  {"m2": 650,  "std": 150},
    "karlıtepe":        {"m2": 620,  "std": 142},
    # ── Bayrampaşa ────────────────────────────────────────────────────────
    "kocatepe":         {"m2": 700,  "std": 158},
    # ── Esenler ───────────────────────────────────────────────────────────
    "fatih mah esen":   {"m2": 580,  "std": 132},
    "menderes":         {"m2": 580,  "std": 132},
    "fevzi çakmak":     {"m2": 580,  "std": 132},
    # ─── ANADOLU YAKASI ────────────────────────────────────────────────────
    # ── Üsküdar ───────────────────────────────────────────────────────────
    "çengelköy":        {"m2": 2200, "std": 430},
    "kuzguncuk":        {"m2": 2000, "std": 400},
    "beylerbeyi":       {"m2": 1700, "std": 340},
    "sultantepe":       {"m2": 1300, "std": 260},
    "bulgurlu":         {"m2": 1200, "std": 248},
    "bağlarbaşı":       {"m2": 1200, "std": 245},
    "cumhuriyet mah üsk":{"m2": 1200,"std": 248},
    "ferah":            {"m2": 1100, "std": 228},
    "bahçelievler üsk": {"m2": 1100, "std": 228},
    "valide-i atik":    {"m2": 1200, "std": 248},
    "ünalan":           {"m2": 1100, "std": 228},
    "kuzguncuk":        {"m2": 2000, "std": 400},
    "mehmet akif ersoy üsk":{"m2": 1150,"std": 238},
    "barbaros mah üsk": {"m2": 1200, "std": 248},
    # ── Beykoz ────────────────────────────────────────────────────────────
    "kavacık":          {"m2": 1400, "std": 280},
    "anadoluhisarı":    {"m2": 1800, "std": 360},
    # ── Kadıköy ───────────────────────────────────────────────────────────
    "moda":             {"m2": 2800, "std": 540},
    "fenerbahçe":       {"m2": 2200, "std": 430},
    "suadiye":          {"m2": 2500, "std": 490},
    "caddebostan":      {"m2": 2500, "std": 490},
    "erenköy":          {"m2": 1800, "std": 360},
    "göztepe":          {"m2": 1600, "std": 320},
    "kozyatağı":        {"m2": 1500, "std": 300},
    "bostancı":         {"m2": 1600, "std": 320},
    "feneryolu":        {"m2": 1800, "std": 360},
    "rasimpaşa":        {"m2": 1400, "std": 280},
    "zühtüpaşa":        {"m2": 1600, "std": 320},
    "caferağa":         {"m2": 1500, "std": 300},
    "merdivenköy":      {"m2": 1400, "std": 280},
    "dumlupınar":       {"m2": 1300, "std": 260},
    "fikirtepe":        {"m2": 1400, "std": 280},
    "eğitim mah":       {"m2": 1300, "std": 260},
    # ── Ataşehir ──────────────────────────────────────────────────────────
    "içerenköy":        {"m2": 1400, "std": 280},
    "küçükbakkalköy":   {"m2": 1200, "std": 245},
    "kayışdağı":        {"m2": 1100, "std": 225},
    "barbaros mah ata": {"m2": 1250, "std": 255},
    "esatpaşa":         {"m2": 1200, "std": 248},
    "ferhatpaşa":       {"m2": 1100, "std": 228},
    "örnek mah":        {"m2": 1200, "std": 248},
    "atatürk mah ata":  {"m2": 1200, "std": 248},
    "yenişehir ata":    {"m2": 1100, "std": 228},
    "inönü mah ata":    {"m2": 1200, "std": 248},
    # ── Maltepe ───────────────────────────────────────────────────────────
    "cevizli":          {"m2": 1050, "std": 215},
    "altıntepe":        {"m2": 950,  "std": 200},
    "maltepe merkez":   {"m2": 950,  "std": 200},
    "fındıklı mah":     {"m2": 950,  "std": 200},
    "çınar mah":        {"m2": 1000, "std": 210},
    "idealtepe":        {"m2": 950,  "std": 200},
    "zümrütevler":      {"m2": 950,  "std": 200},
    "feyzullah":        {"m2": 880,  "std": 188},
    # ── Kartal ────────────────────────────────────────────────────────────
    "kordonboyu":       {"m2": 950,  "std": 200},
    "atalar":           {"m2": 850,  "std": 185},
    "hürriyet mah kart":{"m2": 820,  "std": 178},
    "karlıktepe":       {"m2": 800,  "std": 175},
    # ── Ümraniye ──────────────────────────────────────────────────────────
    "site mah ümr":     {"m2": 1000, "std": 210},
    "armağanevler":     {"m2": 950,  "std": 200},
    "altınşehir":       {"m2": 880,  "std": 188},
    "atatürk mah ümr":  {"m2": 950,  "std": 200},
    "inkılap":          {"m2": 950,  "std": 200},
    "finanskent":       {"m2": 1100, "std": 228},
    "cemil meriç":      {"m2": 880,  "std": 188},
    "istiklal mah ümr": {"m2": 880,  "std": 188},
    "mehmet akif ümr":  {"m2": 880,  "std": 188},
    # ── Pendik ────────────────────────────────────────────────────────────
    "yenişehir pend":   {"m2": 780,  "std": 172},
    "harmandere":       {"m2": 720,  "std": 162},
    "kurtköy":          {"m2": 680,  "std": 154},
    "şeyhli":           {"m2": 700,  "std": 158},
    "güllü bağlar":     {"m2": 700,  "std": 158},
    "ahmet yesevi":     {"m2": 700,  "std": 158},
    "çamlık mah":       {"m2": 750,  "std": 168},
    "esenyalı":         {"m2": 680,  "std": 154},
    # ── Tuzla ─────────────────────────────────────────────────────────────
    "aydınlı":          {"m2": 700,  "std": 158},
    "tepeören":         {"m2": 780,  "std": 172},
    "istasyon mah":     {"m2": 700,  "std": 158},
    "orta mah tuzla":   {"m2": 660,  "std": 150},
    "postane":          {"m2": 680,  "std": 154},
    # ── Sultanbeyli ───────────────────────────────────────────────────────
    "fatih mah sul":    {"m2": 480,  "std": 110},
    "hasanpaşa sul":    {"m2": 460,  "std": 105},
    "mimar sinan sul":  {"m2": 450,  "std": 100},
    "akşemsettin":      {"m2": 460,  "std": 105},
    # ── Sancaktepe ────────────────────────────────────────────────────────
    "inönü mah san":    {"m2": 520,  "std": 120},
    # ── Çekmeköy ──────────────────────────────────────────────────────────
    "taşdelen":         {"m2": 720,  "std": 162},
    "çatalmeşe":        {"m2": 700,  "std": 158},
    "güngören mah çek": {"m2": 700,  "std": 158},
    "mimar sinan çek":  {"m2": 720,  "std": 162},
    "soğukpınar":       {"m2": 700,  "std": 158},
    "mehmet akif çek":  {"m2": 700,  "std": 158},
    "aydınlar":         {"m2": 700,  "std": 158},
    # ── Adalar ────────────────────────────────────────────────────────────
    "maden mah":        {"m2": 1500, "std": 300},
    # ── Başakşehir ────────────────────────────────────────────────────────
    "bahçeşehir":       {"m2": 900,  "std": 190},
    "başak mah":        {"m2": 800,  "std": 175},
    "başakşehir mah":   {"m2": 800,  "std": 175},
    # ── Küçükçekmece ──────────────────────────────────────────────────────
    "tevfik bey":       {"m2": 750,  "std": 168},
    "cennet mah":       {"m2": 750,  "std": 168},
    "sultan murat":     {"m2": 720,  "std": 162},
    "gültepe küç":      {"m2": 700,  "std": 158},
    "kanarya":          {"m2": 700,  "std": 158},
    "yeşilova":         {"m2": 680,  "std": 154},
    "istasyon küç":     {"m2": 700,  "std": 158},
    # ── Silivri ───────────────────────────────────────────────────────────
    "piri mehmet":      {"m2": 500,  "std": 115},
    "mimar sinan sil":  {"m2": 500,  "std": 115},
    "selimpaşa":        {"m2": 520,  "std": 120},
    # ── Şile ──────────────────────────────────────────────────────────────
    "balibey":          {"m2": 500,  "std": 115},
    "imrendere":        {"m2": 500,  "std": 115},
    "hacı kasım":       {"m2": 500,  "std": 115},
    # ── Güngören ──────────────────────────────────────────────────────────
    "merkez mah güng":  {"m2": 700,  "std": 158},
    # ── Zeytinburnu ───────────────────────────────────────────────────────
    "zeytinburnu":      {"m2": 800,  "std": 175},
}

# Tier fallback fiyatları (mahalle bulunamazsa)
TIER_FALLBACK = {
    "luxury": {"m2": 2000, "std": 400},
    "mid":    {"m2": 1000, "std": 210},
    "suburb": {"m2": 550,  "std": 125},
}

LUXURY_DISTRICTS = {
    "beşiktaş", "sarıyer", "şişli", "kadıköy", "bakırköy", "beyoğlu",
}
SUBURB_DISTRICTS = {
    "arnavutköy", "silivri", "çatalca", "şile", "sultanbeyli",
    "sultangazi", "esenyurt", "büyükçekmece", "esenler", "bayrampaşa",
}

# ── Oda → m² aralıkları ──────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# Yardımcı fonksiyonlar
# ─────────────────────────────────────────────────────────────────────────────

def get_tier(konum: str) -> str:
    kl = konum.lower()
    for d in LUXURY_DISTRICTS:
        if d in kl:
            return "luxury"
    for d in SUBURB_DISTRICTS:
        if d in kl:
            return "suburb"
    return "mid"

def lookup_mahalle(konum: str) -> dict | None:
    """Try to find a mahalle-level price entry from the Konum string."""
    kl = konum.lower()
    # Try longest match first (avoids 'merkez mah' matching wrong district)
    best_key = None
    best_len = 0
    for key in MAHALLE_FIYAT:
        if key in kl and len(key) > best_len:
            best_key = key
            best_len = len(key)
    if best_key:
        return MAHALLE_FIYAT[best_key]
    return None


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

    # 3. Oda sayısına göre aralık
    lo, hi = ODA_M2.get(oda, (120, 200))
    first = oda.split("+")[0] if "+" in oda else "2"
    try:
        n = int(first)
    except ValueError:
        n = 2
    if n >= 6:
        lo, hi = 250, 500
    # Hafif normale çek (uniform yerine biraz çarpık dağılım)
    return str(int(random.triangular(lo, hi, lo + (hi - lo) * 0.45)))

def simulate_kat(baslik: str) -> str:
    b = baslik.lower()
    # Açık kat numarası ("5.kat", "3. kat", "5/2. katta")
    m = re.search(r"(\d+)[./](\d+)[\s.]*kat", b)
    if m:
        return m.group(2)
    m = re.search(r"(\d+)\s*\.?(\d*)\s*kat\b", b)
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
    # 1. Başlıkta açık fiyat var mı? ("35.000 TL", "150000tl", "35 000 Tl")
    price_match = re.search(r"(\d[\d\.\s]{2,})\s*[Tt][Ll]", baslik)
    if price_match:
        raw = price_match.group(1).replace(".", "").replace(" ", "")
        try:
            val = int(raw)
            if 5_000 <= val <= 5_000_000:
                return str(val)
        except ValueError:
            pass

    # 2. m² bazlı fiyatlandırma
    mahalle_data = lookup_mahalle(konum)
    tier = get_tier(konum)
    if mahalle_data:
        m2_birim = mahalle_data["m2"]
        std = mahalle_data["std"]
    else:
        fb = TIER_FALLBACK[tier]
        m2_birim = fb["m2"]
        std = fb["std"]

    # Villa/müstakil için m² birimini artır
    villa = is_villa_like(baslik)
    if villa:
        m2_birim = int(m2_birim * 1.4)
        std = int(std * 1.4)

    # m² miktarı
    lo_m2, hi_m2 = ODA_M2.get(oda, (120, 200))
    m2 = random.randint(lo_m2, hi_m2)

    # Fiyat = m² × birim fiyat + gürültü
    noise = random.gauss(0, std)
    fiyat = int(m2 * m2_birim + noise * (m2 ** 0.5))
    fiyat = max(5000, fiyat)
    # 500 TL'ye yuvarla
    fiyat = round(fiyat / 500) * 500
    return str(fiyat)

def simulate_yapi_yasi(baslik: str) -> str:
    b = baslik.lower()
    if any(k in b for k in ["sıfır", "yeni bina", "yeni yapı", "2024", "2025", "2026"]):
        return str(random.choice([0, 1]))
    m = re.search(r"(\d+)\s*yıllık", b)
    if m:
        return m.group(1)
    # Yapım yılı varsa (örn. "2007 yapımı")
    m = re.search(r"\b(19\d{2}|20[0-2]\d)\b", b)
    if m:
        yil = int(m.group(1))
        yas = max(0, 2025 - yil)
        return str(yas)
    return str(random.randint(0, 25))

def simulate_esya(baslik: str) -> str:
    b = baslik.lower()
    if any(k in b for k in ["eşyalı", "mobilyalı", "full eşya", "full mobilya", "eşyali"]):
        return "Eşyalı"
    if any(k in b for k in ["eşyasız", "boş daire", "boş ev", "boyali boş"]):
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

    if tier == "luxury":
        choices = ["Kombi", "Merkezi", "Yerden Isıtma", "Klima (Split)"]
        weights = [45, 35, 12, 8]
    elif tier == "suburb":
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

# ─────────────────────────────────────────────────────────────────────────────
def process_row(row: dict, index: int) -> dict:
    random.seed(index)

    baslik = row.get("Başlık", "")
    konum  = row.get("Konum", "")
    tier   = get_tier(konum)

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
        row["Fiyat"] = simulate_fiyat(baslik, oda, konum)

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

    processed = [process_row(row, i) for i, row in enumerate(rows)]

    with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processed)

    print(f"Done. {len(processed)} rows written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()