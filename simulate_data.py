#!/usr/bin/env python3
"""
Simulate missing values for istanbul_kiralik_complete.csv
and produce istanbul_kiralik_simulated.csv

Pricing model: mahalle-level TL/m² rates derived from
Endeksa.com Mart 2026 Istanbul rental data (ilce ortalamalarından
lüks/orta/ekonomik mahalle katsayılarıyla türetilmiştir).
  Lüks mahalle:     ilce_ort × 1.40–1.55
  Orta mahalle:     ilce_ort × 0.95–1.05
  Ekonomik mahalle: ilce_ort × 0.70–0.75
std = m2_fiyat × 0.18

ILCE_ISTATISTIK tablosu: Endeksa.com Mart 2026 ilçe bazlı satılık veriler.
  m2_kira        – ortalama kira TL/m²
  ort_deger      – satılık ortalama m² fiyatı (TL)
  amortisman_yil – amortisman süresi (yıl)
  getiri         – yıllık kira getirisi (%)
  yillik_degisim – yıllık fiyat değişimi (%)
"""

import csv
import random
import re

INPUT_FILE  = "istanbul_kiralik_complete.csv"
OUTPUT_FILE = "istanbul_kiralik_simulated.csv"

# ─────────────────────────────────────────────────────────────────────────────
# MAHALLE FİYAT TABLOSU
# Kaynak: Endeksa.com Mart 2026 ilçe ortalamaları
# Her ilçe içinde mahalleler lüks / orta / ekonomik olarak gruplandırılmıştır.
# ─────────────────────────────────────────────────────────────────────────────
MAHALLELER: dict[str, dict] = {

    # ── AVRUPA YAKASI ──────────────────────────────────────────────────────────

    "Üst Segment – Boğaz (Avrupa)": {
        # Beşiktaş ilçe ort: 592 TL/m²
        "Beşiktaş": {
            "Bebek":              {"m2_fiyat": 920, "std": 166},
            "Arnavutköy(Beş)":    {"m2_fiyat": 860, "std": 155},
            "Etiler":             {"m2_fiyat": 830, "std": 149},
            "Levent":             {"m2_fiyat": 720, "std": 130},
            "Ortaköy":            {"m2_fiyat": 650, "std": 117},
            "Balmumcu":           {"m2_fiyat": 590, "std": 106},
            "Beşiktaş Merkez":    {"m2_fiyat": 500, "std": 90},
            "Dikilitaş":          {"m2_fiyat": 430, "std": 77},
        },
        # Sarıyer ilçe ort: 590 TL/m²
        "Sarıyer": {
            "Yeniköy":            {"m2_fiyat": 910, "std": 164},
            "Tarabya":            {"m2_fiyat": 860, "std": 155},
            "İstinye":            {"m2_fiyat": 770, "std": 139},
            "Zekeriyaköy":        {"m2_fiyat": 650, "std": 117},
            "Maslak":             {"m2_fiyat": 590, "std": 106},
            "Sarıyer Merkez":     {"m2_fiyat": 500, "std": 90},
            "Rumelifeneri":       {"m2_fiyat": 430, "std": 77},
        },
    },

    "Üst-Orta Segment – Merkez Avrupa": {
        # Şişli ilçe ort: 452 TL/m²
        "Şişli": {
            "Nişantaşı":          {"m2_fiyat": 700, "std": 126},
            "Teşvikiye":          {"m2_fiyat": 650, "std": 117},
            "Fulya":              {"m2_fiyat": 560, "std": 101},
            "Bomonti":            {"m2_fiyat": 510, "std": 92},
            "Mecidiyeköy":        {"m2_fiyat": 450, "std": 81},
            "Şişli Merkez":       {"m2_fiyat": 390, "std": 70},
            "Gülbahar":           {"m2_fiyat": 330, "std": 59},
        },
        # Beyoğlu ilçe ort: 492 TL/m²
        "Beyoğlu": {
            "Cihangir":           {"m2_fiyat": 760, "std": 137},
            "Galata":             {"m2_fiyat": 690, "std": 124},
            "Çukurcuma":          {"m2_fiyat": 640, "std": 115},
            "Karaköy":            {"m2_fiyat": 580, "std": 104},
            "Taksim":             {"m2_fiyat": 540, "std": 97},
            "Beyoğlu Merkez":     {"m2_fiyat": 490, "std": 88},
            "Tarlabaşı":          {"m2_fiyat": 360, "std": 65},
        },
        # Kağıthane ilçe ort: 391 TL/m²
        "Kağıthane": {
            "Seyrantepe":         {"m2_fiyat": 550, "std": 99},
            "Çağlayan":           {"m2_fiyat": 470, "std": 85},
            "Kağıthane Merkez":   {"m2_fiyat": 390, "std": 70},
            "Gültepe":            {"m2_fiyat": 320, "std": 58},
            "Hamidiye":           {"m2_fiyat": 280, "std": 50},
        },
        # Eyüpsultan ilçe ort: 418 TL/m²
        "Eyüpsultan": {
            "Alibeyköy":          {"m2_fiyat": 560, "std": 101},
            "Eyüp Merkez":        {"m2_fiyat": 460, "std": 83},
            "İslambey":           {"m2_fiyat": 420, "std": 76},
            "Rami":               {"m2_fiyat": 340, "std": 61},
            "Topçular":           {"m2_fiyat": 300, "std": 54},
        },
    },

    "Orta Segment – Tarihi Yarımada": {
        # Fatih ilçe ort: 330 TL/m²
        "Fatih": {
            "Sultanahmet":        {"m2_fiyat": 500, "std": 90},
            "Balat":              {"m2_fiyat": 460, "std": 83},
            "Fener":              {"m2_fiyat": 430, "std": 77},
            "Fatih Merkez":       {"m2_fiyat": 330, "std": 59},
            "Samatya":            {"m2_fiyat": 300, "std": 54},
            "Aksaray":            {"m2_fiyat": 280, "std": 50},
            "Topkapı":            {"m2_fiyat": 240, "std": 43},
        },
    },

    "Orta Segment – Güney Avrupa": {
        # Bakırköy ilçe ort: 591 TL/m²
        "Bakırköy": {
            "Ataköy 1-4":         {"m2_fiyat": 890, "std": 160},
            "Ataköy 5-11":        {"m2_fiyat": 800, "std": 144},
            "Yeşilköy":           {"m2_fiyat": 730, "std": 131},
            "Florya":             {"m2_fiyat": 680, "std": 122},
            "Bakırköy Merkez":    {"m2_fiyat": 590, "std": 106},
            "Kartaltepe":         {"m2_fiyat": 430, "std": 77},
        },
        # Zeytinburnu ilçe ort: 585 TL/m²
        "Zeytinburnu": {
            "Yeşiltepe":          {"m2_fiyat": 820, "std": 148},
            "Kazlıçeşme":         {"m2_fiyat": 680, "std": 122},
            "Seyitnizam":         {"m2_fiyat": 590, "std": 106},
            "Veliefendi":         {"m2_fiyat": 520, "std": 94},
            "Merkezefendi":       {"m2_fiyat": 420, "std": 76},
        },
        # Bahçelievler ilçe ort: 393 TL/m²
        "Bahçelievler": {
            "Yenibosna":          {"m2_fiyat": 550, "std": 99},
            "Bahçelievler Mrk.":  {"m2_fiyat": 430, "std": 77},
            "Şirinevler":         {"m2_fiyat": 390, "std": 70},
            "Soğanlı":            {"m2_fiyat": 340, "std": 61},
            "Kocasinan":          {"m2_fiyat": 280, "std": 50},
        },
        # Güngören ilçe ort: 326 TL/m²
        "Güngören": {
            "Güngören Merkez":    {"m2_fiyat": 460, "std": 83},
            "Tozkoparan":         {"m2_fiyat": 390, "std": 70},
            "Mehmetçik":          {"m2_fiyat": 330, "std": 59},
            "Sefaköy":            {"m2_fiyat": 240, "std": 43},
        },
        # Küçükçekmece ilçe ort: 367 TL/m²
        "Küçükçekmece": {
            "Atakent":            {"m2_fiyat": 520, "std": 94},
            "Halkalı":            {"m2_fiyat": 430, "std": 77},
            "Küçükçekmece Mrk.":  {"m2_fiyat": 370, "std": 67},
            "İnönü":              {"m2_fiyat": 310, "std": 56},
            "Tevfikbey":          {"m2_fiyat": 265, "std": 48},
        },
    },

    "Alt-Orta Segment – Batı Avrupa": {
        # Bağcılar ilçe ort: 297 TL/m²
        "Bağcılar": {
            "Güneşli":            {"m2_fiyat": 420, "std": 76},
            "Mahmutbey":          {"m2_fiyat": 360, "std": 65},
            "Bağcılar Merkez":    {"m2_fiyat": 300, "std": 54},
            "Kirazlı":            {"m2_fiyat": 270, "std": 49},
            "Sefaköy(Bağ)":       {"m2_fiyat": 215, "std": 39},
        },
        # Avcılar ilçe ort: 307 TL/m²
        "Avcılar": {
            "Denizköşkler":       {"m2_fiyat": 430, "std": 77},
            "Avcılar Merkez":     {"m2_fiyat": 370, "std": 67},
            "Cihangir(Avc)":      {"m2_fiyat": 310, "std": 56},
            "Ambarlı":            {"m2_fiyat": 255, "std": 46},
            "Firuzköy":           {"m2_fiyat": 220, "std": 40},
        },
        # Beylikdüzü ilçe ort: 289 TL/m²
        "Beylikdüzü": {
            "Büyükşehir":         {"m2_fiyat": 410, "std": 74},
            "Gürpınar":           {"m2_fiyat": 360, "std": 65},
            "Beylikdüzü Mrk.":    {"m2_fiyat": 290, "std": 52},
            "Adnan Kahveci":      {"m2_fiyat": 250, "std": 45},
            "Cumhuriyet":         {"m2_fiyat": 210, "std": 38},
        },
        # Bayrampaşa ilçe ort: 326 TL/m²
        "Bayrampaşa": {
            "Yıldırım":           {"m2_fiyat": 460, "std": 83},
            "Bayrampaşa Merkez":  {"m2_fiyat": 360, "std": 65},
            "Muratpaşa":          {"m2_fiyat": 330, "std": 59},
            "Altıntepsi":         {"m2_fiyat": 235, "std": 42},
        },
        # Gaziosmanpaşa ilçe ort: 294 TL/m²
        "Gaziosmanpaşa": {
            "Karadeniz":          {"m2_fiyat": 415, "std": 75},
            "GOP Merkez":         {"m2_fiyat": 330, "std": 59},
            "Fevzi Çakmak(GOP)":  {"m2_fiyat": 295, "std": 53},
            "Karlıtepe":          {"m2_fiyat": 250, "std": 45},
            "Yenidoğan(GOP)":     {"m2_fiyat": 210, "std": 38},
        },
        # Başakşehir ilçe ort: 357 TL/m²
        "Başakşehir": {
            "Başakşehir 4.etap":  {"m2_fiyat": 500, "std": 90},
            "Başakşehir 5.etap":  {"m2_fiyat": 470, "std": 85},
            "Başakşehir Mrk.":    {"m2_fiyat": 360, "std": 65},
            "Kayabaşı":           {"m2_fiyat": 310, "std": 56},
            "İkitelli":           {"m2_fiyat": 260, "std": 47},
        },
        # Esenyurt ilçe ort: 228 TL/m²
        "Esenyurt": {
            "Esenyurt Merkez":    {"m2_fiyat": 320, "std": 58},
            "Fatih Mah.(Esen)":   {"m2_fiyat": 260, "std": 47},
            "Pınar":              {"m2_fiyat": 230, "std": 41},
            "Saadetdere":         {"m2_fiyat": 200, "std": 36},
            "Mehterçeşme":        {"m2_fiyat": 165, "std": 30},
        },
        # Büyükçekmece ilçe ort: 282 TL/m²
        "Büyükçekmece": {
            "Kumburgaz":          {"m2_fiyat": 395, "std": 71},
            "Büyükçekmece Mrk.":  {"m2_fiyat": 310, "std": 56},
            "Mimaroba":           {"m2_fiyat": 285, "std": 51},
            "Gürpınar(Büy)":      {"m2_fiyat": 240, "std": 43},
            "Tepecik":            {"m2_fiyat": 205, "std": 37},
        },
        # Esenler ilçe ort: 251 TL/m²
        "Esenler": {
            "Tuna":               {"m2_fiyat": 355, "std": 64},
            "Esenler Merkez":     {"m2_fiyat": 280, "std": 50},
            "Havaalanı":          {"m2_fiyat": 250, "std": 45},
            "Nenehatun":          {"m2_fiyat": 215, "std": 39},
            "Menderes":           {"m2_fiyat": 180, "std": 32},
        },
        # Sultangazi ilçe ort: 237 TL/m²
        "Sultangazi": {
            "Uğur Mumcu(Sul)":    {"m2_fiyat": 335, "std": 60},
            "Sultangazi Merkez":  {"m2_fiyat": 265, "std": 48},
            "Cebeci":             {"m2_fiyat": 240, "std": 43},
            "Habibler":           {"m2_fiyat": 200, "std": 36},
            "Gazi":               {"m2_fiyat": 170, "std": 31},
        },
        # Arnavutköy ilçe ort: 240 TL/m²
        "Arnavutköy": {
            "Hadımköy":           {"m2_fiyat": 340, "std": 61},
            "Arnavutköy Merkez":  {"m2_fiyat": 270, "std": 49},
            "Bolluca":            {"m2_fiyat": 240, "std": 43},
            "Haraçcı":            {"m2_fiyat": 200, "std": 36},
            "İmrahor":            {"m2_fiyat": 175, "std": 32},
        },
        # Silivri ilçe ort: 247 TL/m²
        "Silivri": {
            "Silivri Merkez":     {"m2_fiyat": 350, "std": 63},
            "Selimpaşa":          {"m2_fiyat": 290, "std": 52},
            "Silivri Çiftlikköy": {"m2_fiyat": 250, "std": 45},
            "Fener(Sil)":         {"m2_fiyat": 210, "std": 38},
            "Ortaköy(Sil)":       {"m2_fiyat": 180, "std": 32},
        },
        # Çatalca ilçe ort: 294 TL/m²
        "Çatalca": {
            "Çatalca Merkez":     {"m2_fiyat": 415, "std": 75},
            "Ferhatpaşa(Çat)":    {"m2_fiyat": 345, "std": 62},
            "Kaleiçi":            {"m2_fiyat": 295, "std": 53},
            "Karacaköy":          {"m2_fiyat": 245, "std": 44},
            "Elbasan":            {"m2_fiyat": 215, "std": 39},
        },
    },

    # ── ANADOLU YAKASI ─────────────────────────────────────────────────────────

    "Üst Segment – Boğaz (Anadolu)": {
        # Üsküdar ilçe ort: 425 TL/m²
        "Üsküdar": {
            "Çengelköy":          {"m2_fiyat": 660, "std": 119},
            "Kuzguncuk":          {"m2_fiyat": 610, "std": 110},
            "Beylerbeyi":         {"m2_fiyat": 560, "std": 101},
            "Acıbadem(Üsk)":      {"m2_fiyat": 510, "std": 92},
            "Üsküdar Merkez":     {"m2_fiyat": 425, "std": 77},
            "Bağlarbaşı":         {"m2_fiyat": 390, "std": 70},
            "Ümraniye(Üsk)":      {"m2_fiyat": 310, "std": 56},
        },
        # Beykoz ilçe ort: 356 TL/m²
        "Beykoz": {
            "Anadoluhisarı":      {"m2_fiyat": 550, "std": 99},
            "Kavacık":            {"m2_fiyat": 470, "std": 85},
            "Beykoz Merkez":      {"m2_fiyat": 360, "std": 65},
            "Paşabahçe":          {"m2_fiyat": 310, "std": 56},
            "Çubuklu":            {"m2_fiyat": 260, "std": 47},
        },
        # Adalar ilçe ort: 547 TL/m²
        "Adalar": {
            "Büyükada":           {"m2_fiyat": 770, "std": 139},
            "Heybeliada":         {"m2_fiyat": 640, "std": 115},
            "Burgazada":          {"m2_fiyat": 550, "std": 99},
            "Kınalıada":          {"m2_fiyat": 470, "std": 85},
            "Adalar Merkez":      {"m2_fiyat": 400, "std": 72},
        },
    },

    "Üst-Orta Segment – Anadolu Merkez": {
        # Kadıköy ilçe ort: 651 TL/m²
        "Kadıköy": {
            "Moda":               {"m2_fiyat": 1010, "std": 182},
            "Fenerbahçe":         {"m2_fiyat": 930,  "std": 167},
            "Bağdat Caddesi":     {"m2_fiyat": 880,  "std": 158},
            "Caddebostan":        {"m2_fiyat": 830,  "std": 149},
            "Erenköy":            {"m2_fiyat": 750,  "std": 135},
            "Acıbadem(Kad)":      {"m2_fiyat": 680,  "std": 122},
            "Göztepe":            {"m2_fiyat": 650,  "std": 117},
            "Kozyatağı":          {"m2_fiyat": 580,  "std": 104},
            "Kadıköy Merkez":     {"m2_fiyat": 540,  "std": 97},
            "Bostancı":           {"m2_fiyat": 470,  "std": 85},
        },
        # Ataşehir ilçe ort: 460 TL/m²
        "Ataşehir": {
            "İçerenköy":          {"m2_fiyat": 650,  "std": 117},
            "Barbaros":           {"m2_fiyat": 590,  "std": 106},
            "Ataşehir Merkez":    {"m2_fiyat": 520,  "std": 94},
            "Küçükbakkalköy":     {"m2_fiyat": 460,  "std": 83},
            "Kayışdağı":          {"m2_fiyat": 400,  "std": 72},
            "Ferhatpaşa":         {"m2_fiyat": 335,  "std": 60},
        },
        # Maltepe ilçe ort: 440 TL/m²
        "Maltepe": {
            "Cevizli":            {"m2_fiyat": 620, "std": 112},
            "Bağlarbaşı(Mal)":    {"m2_fiyat": 560, "std": 101},
            "Maltepe Merkez":     {"m2_fiyat": 490, "std": 88},
            "Altayçeşme":         {"m2_fiyat": 440, "std": 79},
            "Büyükbakkalköy":     {"m2_fiyat": 370, "std": 67},
            "Aydınevler":         {"m2_fiyat": 320, "std": 58},
        },
    },

    "Orta Segment – Anadolu Orta Kuşak": {
        # Kartal ilçe ort: 413 TL/m²
        "Kartal": {
            "Kordonboyu":         {"m2_fiyat": 580, "std": 104},
            "Uğur Mumcu(Kar)":    {"m2_fiyat": 500, "std": 90},
            "Kartal Merkez":      {"m2_fiyat": 415, "std": 75},
            "Yakacık":            {"m2_fiyat": 370, "std": 67},
            "Petrol İş":          {"m2_fiyat": 300, "std": 54},
        },
        # Ümraniye ilçe ort: 374 TL/m²
        "Ümraniye": {
            "Site":               {"m2_fiyat": 530, "std": 95},
            "Namık Kemal":        {"m2_fiyat": 460, "std": 83},
            "Ümraniye Merkez":    {"m2_fiyat": 375, "std": 68},
            "Dudullu":            {"m2_fiyat": 330, "std": 59},
            "Çakmak":             {"m2_fiyat": 285, "std": 51},
            "Alemdağ":            {"m2_fiyat": 270, "std": 49},
        },
        # Çekmeköy ilçe ort: 364 TL/m²
        "Çekmeköy": {
            "Çekmeköy Merkez":    {"m2_fiyat": 510, "std": 92},
            "Taşdelen":           {"m2_fiyat": 450, "std": 81},
            "Nişantepe":          {"m2_fiyat": 365, "std": 66},
            "Mehmet Akif(Çek)":   {"m2_fiyat": 310, "std": 56},
            "Ömerli":             {"m2_fiyat": 265, "std": 48},
        },
        # Pendik ilçe ort: 330 TL/m²
        "Pendik": {
            "İçmeler(Pen)":       {"m2_fiyat": 470, "std": 85},
            "Yenişehir(Pen)":     {"m2_fiyat": 410, "std": 74},
            "Kaynarca":           {"m2_fiyat": 370, "std": 67},
            "Pendik Merkez":      {"m2_fiyat": 330, "std": 59},
            "Kurtköy":            {"m2_fiyat": 280, "std": 50},
            "Dolayoba":           {"m2_fiyat": 240, "std": 43},
        },
    },

    "Alt-Orta Segment – Anadolu Dış Kuşak": {
        # Tuzla ilçe ort: 322 TL/m²
        "Tuzla": {
            "İçmeler(Tuz)":       {"m2_fiyat": 455, "std": 82},
            "Aydıntepe":          {"m2_fiyat": 390, "std": 70},
            "Tuzla Merkez":       {"m2_fiyat": 325, "std": 59},
            "Aydınlı":            {"m2_fiyat": 280, "std": 50},
            "Mimar Sinan":        {"m2_fiyat": 235, "std": 42},
        },
        # Sultanbeyli ilçe ort: 262 TL/m²
        "Sultanbeyli": {
            "Mehmet Akif(Sul)":   {"m2_fiyat": 370, "std": 67},
            "Sultanbeyli Mrk.":   {"m2_fiyat": 300, "std": 54},
            "Hasanpaşa(Sul)":     {"m2_fiyat": 265, "std": 48},
            "Battalgazi":         {"m2_fiyat": 230, "std": 41},
            "Fatih(Sul)":         {"m2_fiyat": 190, "std": 34},
        },
        # Sancaktepe ilçe ort: 294 TL/m²
        "Sancaktepe": {
            "Samandıra":          {"m2_fiyat": 415, "std": 75},
            "Sancaktepe Mrk.":    {"m2_fiyat": 345, "std": 62},
            "Yenidoğan(San)":     {"m2_fiyat": 295, "std": 53},
            "Eyüp Sultan(San)":   {"m2_fiyat": 255, "std": 46},
            "Sarıgazi":           {"m2_fiyat": 215, "std": 39},
        },
        # Şile ilçe ort: 375 TL/m²
        "Şile": {
            "Şile Merkez":        {"m2_fiyat": 530, "std": 95},
            "Ağva":               {"m2_fiyat": 440, "std": 79},
            "Kumbaba":            {"m2_fiyat": 375, "std": 68},
            "Doğancılı":          {"m2_fiyat": 315, "std": 57},
            "Üvezli":             {"m2_fiyat": 275, "std": 50},
        },
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# İLÇE İSTATİSTİK TABLOSU
# Kaynak: Endeksa.com Mart 2026
# m2_kira        – ortalama kira TL/m²
# ort_deger      – satılık ortalama m² fiyatı (TL)
# amortisman_yil – amortisman süresi (yıl)
# getiri         – yıllık kira getirisi (%)
# yillik_degisim – yıllık fiyat değişimi (%)
# ─────────────────────────────────────────────────────────────────────────────
ILCE_ISTATISTIK: dict[str, dict] = {
    "Esenyurt":       {"m2_kira": 228, "ort_deger": 21632, "amortisman_yil": 11, "getiri": 9.33, "yillik_degisim": 34.53},
    "Sultangazi":     {"m2_kira": 237, "ort_deger": 23698, "amortisman_yil": 14, "getiri": 7.03, "yillik_degisim": 28.28},
    "Arnavutköy":     {"m2_kira": 240, "ort_deger": 22821, "amortisman_yil": 15, "getiri": 6.82, "yillik_degisim": 33.32},
    "Silivri":        {"m2_kira": 247, "ort_deger": 26923, "amortisman_yil": 15, "getiri": 6.59, "yillik_degisim": 33.84},
    "Esenler":        {"m2_kira": 251, "ort_deger": 22799, "amortisman_yil": 15, "getiri": 6.57, "yillik_degisim": 38.65},
    "Sultanbeyli":    {"m2_kira": 262, "ort_deger": 26198, "amortisman_yil": 16, "getiri": 6.18, "yillik_degisim": 30.48},
    "Büyükçekmece":   {"m2_kira": 282, "ort_deger": 35855, "amortisman_yil": 16, "getiri": 6.39, "yillik_degisim": 34.85},
    "Beylikdüzü":     {"m2_kira": 289, "ort_deger": 36182, "amortisman_yil": 13, "getiri": 7.98, "yillik_degisim": 35.69},
    "Sancaktepe":     {"m2_kira": 294, "ort_deger": 29081, "amortisman_yil": 15, "getiri": 6.74, "yillik_degisim": 31.33},
    "Çatalca":        {"m2_kira": 294, "ort_deger": 28795, "amortisman_yil": 15, "getiri": 6.75, "yillik_degisim": 37.88},
    "Gaziosmanpaşa":  {"m2_kira": 294, "ort_deger": 28211, "amortisman_yil": 14, "getiri": 7.39, "yillik_degisim": 28.79},
    "Bağcılar":       {"m2_kira": 297, "ort_deger": 28803, "amortisman_yil": 14, "getiri": 7.05, "yillik_degisim": 47.72},
    "Avcılar":        {"m2_kira": 307, "ort_deger": 31625, "amortisman_yil": 13, "getiri": 7.60, "yillik_degisim": 52.78},
    "Tuzla":          {"m2_kira": 322, "ort_deger": 32842, "amortisman_yil": 16, "getiri": 6.25, "yillik_degisim": 23.28},
    "Bayrampaşa":     {"m2_kira": 326, "ort_deger": 30665, "amortisman_yil": 14, "getiri": 6.99, "yillik_degisim": 38.00},
    "Güngören":       {"m2_kira": 326, "ort_deger": 35567, "amortisman_yil": 12, "getiri": 8.07, "yillik_degisim": 53.49},
    "Fatih":          {"m2_kira": 330, "ort_deger": 26374, "amortisman_yil": 11, "getiri": 8.80, "yillik_degisim": 41.54},
    "Pendik":         {"m2_kira": 330, "ort_deger": 33000, "amortisman_yil": 16, "getiri": 6.32, "yillik_degisim": 31.99},
    "Beykoz":         {"m2_kira": 356, "ort_deger": 43056, "amortisman_yil": 32, "getiri": 3.10, "yillik_degisim": 29.26},
    "Başakşehir":     {"m2_kira": 357, "ort_deger": 41409, "amortisman_yil": 15, "getiri": 6.46, "yillik_degisim": 33.23},
    "Çekmeköy":       {"m2_kira": 364, "ort_deger": 34951, "amortisman_yil": 14, "getiri": 6.95, "yillik_degisim": 35.49},
    "Küçükçekmece":   {"m2_kira": 367, "ort_deger": 34160, "amortisman_yil": 12, "getiri": 8.10, "yillik_degisim": 45.31},
    "Ümraniye":       {"m2_kira": 374, "ort_deger": 35507, "amortisman_yil": 16, "getiri": 6.41, "yillik_degisim": 30.31},
    "Şile":           {"m2_kira": 375, "ort_deger": 42339, "amortisman_yil": 19, "getiri": 5.23, "yillik_degisim": 25.95},
    "Kağıthane":      {"m2_kira": 391, "ort_deger": 33592, "amortisman_yil": 14, "getiri": 7.33, "yillik_degisim": 31.33},
    "Bahçelievler":   {"m2_kira": 393, "ort_deger": 37347, "amortisman_yil": 12, "getiri": 8.59, "yillik_degisim": 75.96},
    "Kartal":         {"m2_kira": 413, "ort_deger": 41340, "amortisman_yil": 15, "getiri": 6.67, "yillik_degisim": 45.89},
    "Eyüpsultan":     {"m2_kira": 418, "ort_deger": 40138, "amortisman_yil": 14, "getiri": 7.31, "yillik_degisim": 38.49},
    "Üsküdar":        {"m2_kira": 425, "ort_deger": 42946, "amortisman_yil": 20, "getiri": 4.98, "yillik_degisim": 34.13},
    "Maltepe":        {"m2_kira": 440, "ort_deger": 39584, "amortisman_yil": 16, "getiri": 6.11, "yillik_degisim": 38.91},
    "Şişli":          {"m2_kira": 452, "ort_deger": 40694, "amortisman_yil": 14, "getiri": 7.06, "yillik_degisim": 34.08},
    "Ataşehir":       {"m2_kira": 460, "ort_deger": 41364, "amortisman_yil": 15, "getiri": 6.68, "yillik_degisim": 37.48},
    "Beyoğlu":        {"m2_kira": 492, "ort_deger": 40866, "amortisman_yil": 12, "getiri": 8.26, "yillik_degisim": 40.81},
    "Adalar":         {"m2_kira": 547, "ort_deger": None, "amortisman_yil": None, "getiri": None, "yillik_degisim": None},
    "Zeytinburnu":    {"m2_kira": 585, "ort_deger": 59079, "amortisman_yil": 12, "getiri": 8.58, "yillik_degisim": 104.71},
    "Sarıyer":        {"m2_kira": 590, "ort_deger": 72021, "amortisman_yil": 21, "getiri": 4.79, "yillik_degisim": 24.43},
    "Bakırköy":       {"m2_kira": 591, "ort_deger": 69712, "amortisman_yil": 17, "getiri": 5.95, "yillik_degisim": 56.14},
    "Beşiktaş":       {"m2_kira": 592, "ort_deger": 61587, "amortisman_yil": 24, "getiri": 4.19, "yillik_degisim": 26.44},
    "Kadıköy":        {"m2_kira": 651, "ort_deger": 71645, "amortisman_yil": 20, "getiri": 4.92, "yillik_degisim": 41.69},
}

# ── Tier fallback (mahalle bulunamazsa ilçe ortalamalarına dayalı değerler) ───
TIER_FALLBACK = {
    "üst":      {"m2_fiyat": 620, "std": 112},
    "üst-orta": {"m2_fiyat": 460, "std": 83},
    "orta":     {"m2_fiyat": 370, "std": 67},
    "alt-orta": {"m2_fiyat": 270, "std": 49},
    "alt":      {"m2_fiyat": 200, "std": 36},
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
    luxury = {"beşiktaş", "sarıyer", "kadıköy", "şişli", "beyoğlu", "bakırköy", "üsküdar", "adalar"}
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

    noise = random.gauss(0, std)
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
        return str(max(0, 2026 - yil))
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

# ─────────────────────────────────────────────────────────────────────────────
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