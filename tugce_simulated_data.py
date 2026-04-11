#!/usr/bin/env python3
"""
Simulate missing values for istanbul_kiralik_complete.csv
and produce istanbul_kiralik_simulated.csv

Pricing model: mahalle-level TL/m² rates derived from
Endeksa.com Mart 2026 Istanbul rental data.

Dynamic pricing: ilce_ort × mahalle_katsayi
  Lüks mahalle:     katsayi 1.35–1.60
  Orta mahalle:     katsayi 0.90–1.05
  Ekonomik mahalle: katsayi 0.65–0.80

Soft clamp: MIN_KATSAYI=0.65, MAX_KATSAYI=1.60
std = m2_fiyat × 0.08  (eski: 0.18)
"""

import csv
import random
import re

INPUT_FILE  = "istanbul_kiralik_complete.csv"
OUTPUT_FILE = "istanbul_kiralik_simulated.csv"

# ──────────────────────────────────────────────────────────────────
# SOFT CLAMP SINIRLARI
# ──────────────────────────────────────────────────────────────────
MIN_KATSAYI = 0.65
MAX_KATSAYI = 1.60

# ──────────────────────────────────────────────────────────────────
# İLÇE ORTALAMA KİRA (TL/m²) — Endeksa Mart 2026
# ──────────────────────────────────────────────────────────────────
ILCE_ORT: dict[str, int] = {
    "Esenyurt": 228, "Sultangazi": 237, "Arnavutköy": 240, "Silivri": 247,
    "Esenler": 251, "Sultanbeyli": 262, "Büyükçekmece": 282, "Beylikdüzü": 289,
    "Sancaktepe": 294, "Çatalca": 294, "Gaziosmanpaşa": 294, "Bağcılar": 297,
    "Avcılar": 307, "Tuzla": 322, "Bayrampaşa": 326, "Güngören": 326,
    "Fatih": 330, "Pendik": 330, "Beykoz": 356, "Başakşehir": 357,
    "Çekmeköy": 364, "Küçükçekmece": 367, "Ümraniye": 374, "Şile": 375,
    "Kağıthane": 391, "Bahçelievler": 393, "Kartal": 413, "Eyüpsultan": 418,
    "Üsküdar": 425, "Maltepe": 440, "Şişli": 452, "Ataşehir": 460,
    "Beyoğlu": 492, "Adalar": 547, "Zeytinburnu": 585, "Sarıyer": 590,
    "Bakırköy": 591, "Beşiktaş": 592, "Kadıköy": 651,
}

# ──────────────────────────────────────────────────────────────────
# MAHALLE FİYAT TABLOSU
# Kaynak: Endeksa.com Mart 2026 ilçe ortalamaları
# Her ilçe içinde mahalleler lüks / orta / ekonomik olarak gruplandırılmıştır.
#
# ÖNEMLİ: Gerçek mahalle isimleri (CSV'deki "Mah." formatı) da alias
#          olarak eklenmiştir — lookup_mahalle eşleşmesi için.
# ──────────────────────────────────────────────────────────────────
MAHALLELER: dict[str, dict] = {

    # ── AVRUPA YAKASI ──────────────────────────────────────────────

    "Üst Segment – Boğaz (Avrupa)": {
        # Beşiktaş ilçe ort: 592 TL/m²
        "Beşiktaş": {
            "Bebek":              {"katsayi": 1.55},
            "Arnavutköy(Beş)":    {"katsayi": 1.45},
            "Etiler":             {"katsayi": 1.40},
            "Nisbetiye":          {"katsayi": 1.40},
            "Akat":               {"katsayi": 1.38},
            "Ulus":               {"katsayi": 1.38},
            "Levazım":            {"katsayi": 1.35},
            "Levent":             {"katsayi": 1.22},
            "Gayrettepe":         {"katsayi": 1.18},
            "Ortaköy":            {"katsayi": 1.10},
            "Mecidiye":           {"katsayi": 1.10},
            "Cihannüma":          {"katsayi": 1.08},
            "Abbasağa":           {"katsayi": 1.05},
            "Muradiye":           {"katsayi": 1.05},
            "Türkali":            {"katsayi": 1.45},  # Akaretler bölgesi
            "Sinanpaşa":          {"katsayi": 1.15},
            "Balmumcu":           {"katsayi": 1.00},
            "Beşiktaş Merkez":    {"katsayi": 0.84},
            "Dikilitaş":          {"katsayi": 0.73},
            "Yıldız":             {"katsayi": 1.12},
            "Konaklar":           {"katsayi": 1.35},
            "Kuruçeşme":          {"katsayi": 1.30},
            "Vişnezade":          {"katsayi": 1.10},
        },
        # Sarıyer ilçe ort: 590 TL/m²
        "Sarıyer": {
            "Yeniköy":            {"katsayi": 1.54},
            "Tarabya":            {"katsayi": 1.10},
            "İstinye":            {"katsayi": 1.31},
            "Zekeriyaköy":        {"katsayi": 1.10},
            "Maslak":             {"katsayi": 1.00},
            "Sarıyer Merkez":     {"katsayi": 0.85},
            "Rumelifeneri":       {"katsayi": 0.73},
            "Rumeli Kavağı":      {"katsayi": 0.75},
            "Bahçeköy":           {"katsayi": 0.90},
            "Büyükdere":          {"katsayi": 0.88},
            "Reşitpaşa":         {"katsayi": 0.95},
            "Çayırbaşı":          {"katsayi": 0.92},
            "Uskumruköy":         {"katsayi": 0.90},
            "Ferahevler":         {"katsayi": 0.88},
            "Kireçburnu":         {"katsayi": 0.90},
            "Çamlıtepe":          {"katsayi": 0.85},
            "Cumhuriyet(Sar)":    {"katsayi": 0.88},
            "Ayazağa":            {"katsayi": 1.05},
            "Huzur":              {"katsayi": 1.00},
            "Poligon":            {"katsayi": 0.95},
            "Pınar(Sar)":         {"katsayi": 0.90},
            "Fatih Sultan Mehmet": {"katsayi": 0.92},
            "Darüşşafaka":        {"katsayi": 0.90},
            "Emirgan":            {"katsayi": 1.25},
        },
    },

    "Üst-Orta Segment – Merkez Avrupa": {
        # Şişli ilçe ort: 452 TL/m²
        "Şişli": {
            "Nişantaşı":          {"katsayi": 1.55},
            "Teşvikiye":          {"katsayi": 1.44},
            "Harbiye":            {"katsayi": 1.42},
            "Osmanbey":           {"katsayi": 1.40},
            "Cumhuriyet":         {"katsayi": 1.38},  # Şişli Cumhuriyet Mah.
            "Fulya":              {"katsayi": 1.24},
            "Esentepe":           {"katsayi": 1.18},
            "Bomonti":            {"katsayi": 1.13},
            "Feriköy":            {"katsayi": 1.08},
            "Mecidiyeköy":        {"katsayi": 1.00},
            "Halaskargazi":       {"katsayi": 1.05},
            "Ergenekon":          {"katsayi": 1.02},
            "Şişli Merkez":       {"katsayi": 0.86},
            "Gülbahar":           {"katsayi": 0.73},
            "İnönü(Şişli)":       {"katsayi": 0.95},
            "Kuştepe":            {"katsayi": 0.75},
            "Paşa":               {"katsayi": 1.00},
        },
        # Beyoğlu ilçe ort: 492 TL/m²
        "Beyoğlu": {
            "Cihangir":           {"katsayi": 1.54},
            "Galata":             {"katsayi": 1.40},
            "Çukurcuma":          {"katsayi": 1.30},
            "Firuzağa":           {"katsayi": 1.35},
            "Tomtom":             {"katsayi": 1.38},
            "Gümüşsuyu":          {"katsayi": 1.32},
            "Asmalımescit":       {"katsayi": 1.28},
            "Karaköy":            {"katsayi": 1.18},
            "Taksim":             {"katsayi": 1.10},
            "Beyoğlu Merkez":     {"katsayi": 1.00},
            "Tarlabaşı":          {"katsayi": 0.73},
            "Pürtelaş":           {"katsayi": 0.85},
            "Kaptanpaşa":         {"katsayi": 0.82},
            "Kemankeş":           {"katsayi": 1.20},
            "Örnektepe":          {"katsayi": 0.78},
            "Halıcıoğlu":         {"katsayi": 0.80},
            "Kulaksız":           {"katsayi": 0.82},
            "Sütlüce":            {"katsayi": 0.90},
            "Müeyyetzade":        {"katsayi": 1.15},
            "Evliya Çelebi":      {"katsayi": 1.10},
            "Katip Mustafa Çelebi": {"katsayi": 1.30},
        },
        # Kağıthane ilçe ort: 391 TL/m²
        "Kağıthane": {
            "Seyrantepe":         {"katsayi": 1.41},
            "Çağlayan":           {"katsayi": 1.20},
            "Kağıthane Merkez":   {"katsayi": 1.00},
            "Gültepe":            {"katsayi": 0.82},
            "Hamidiye":           {"katsayi": 0.72},
            "Ortabayır":          {"katsayi": 0.95},
            "Gürsel":             {"katsayi": 0.88},
            "Harmantepe":         {"katsayi": 0.90},
            "Nurtepe":            {"katsayi": 0.78},
            "Şirintepe":          {"katsayi": 0.80},
            "Telsizler":          {"katsayi": 0.85},
            "Yahya Kemal":        {"katsayi": 0.82},
            "Merkez(Kağ)":        {"katsayi": 1.00},
            "Emniyet Evleri":     {"katsayi": 0.92},
            "Hürriyet":           {"katsayi": 0.88},
            "Talatpaşa":          {"katsayi": 0.95},
        },
        # Eyüpsultan ilçe ort: 418 TL/m²
        "Eyüpsultan": {
            "Alibeyköy":          {"katsayi": 1.34},
            "Göktürk":            {"katsayi": 1.40},
            "Kemerburgaz":        {"katsayi": 1.20},
            "Eyüp Merkez":        {"katsayi": 1.10},
            "İslambey":           {"katsayi": 1.00},
            "Rami":               {"katsayi": 0.81},
            "Topçular":           {"katsayi": 0.72},
            "Silahtarağa":        {"katsayi": 0.85},
            "Nişancı":            {"katsayi": 0.90},
            "Düğmeciler":         {"katsayi": 0.80},
            "Defterdar":          {"katsayi": 0.95},
            "Akşemsettin(Eyüp)":  {"katsayi": 0.88},
        },
    },

    "Orta Segment – Tarihi Yarımada": {
        # Fatih ilçe ort: 330 TL/m²
        "Fatih": {
            "Sultanahmet":        {"katsayi": 1.52},
            "Balat":              {"katsayi": 1.39},
            "Fener":              {"katsayi": 1.30},
            "Fatih Merkez":       {"katsayi": 1.00},
            "Samatya":            {"katsayi": 0.91},
            "Aksaray":            {"katsayi": 0.85},
            "Topkapı":            {"katsayi": 0.73},
            "Karagümrük":         {"katsayi": 0.90},
            "Vatan":              {"katsayi": 0.85},
            "Çapa":               {"katsayi": 0.88},
            "Şehremini":          {"katsayi": 0.82},
            "Cerrahpaşa":         {"katsayi": 0.85},
            "Haseki":             {"katsayi": 0.80},
            "Molla Gürani":       {"katsayi": 0.90},
            "Zeyrek":             {"katsayi": 1.10},
            "Küçükayasofya":      {"katsayi": 1.20},
            "Süleymaniye":        {"katsayi": 1.15},
            "Beyazıt":            {"katsayi": 1.00},
            "Kumkapı":            {"katsayi": 0.85},
            "Yedikule":           {"katsayi": 0.78},
            "Silivrikapı":        {"katsayi": 0.75},
        },
    },

    "Orta Segment – Güney Avrupa": {
        # Bakırköy ilçe ort: 591 TL/m²
        "Bakırköy": {
            "Ataköy 1-4":         {"katsayi": 1.51},
            "Ataköy 5-11":        {"katsayi": 1.35},
            "Ataköy 2-5-6":       {"katsayi": 1.40},
            "Ataköy 7-8-9-10":    {"katsayi": 1.38},
            "Ataköy":             {"katsayi": 1.40},
            "Yeşilköy":           {"katsayi": 1.24},
            "Florya":             {"katsayi": 1.15},
            "Bakırköy Merkez":    {"katsayi": 1.00},
            "Kartaltepe":         {"katsayi": 0.73},
            "Zuhuratbaba":        {"katsayi": 0.85},
            "Osmaniye":           {"katsayi": 0.88},
            "Cevizlik":           {"katsayi": 0.90},
            "Sakızağacı":         {"katsayi": 0.82},
            "Şenlik":             {"katsayi": 0.80},
            "Yenimahalle(Bak)":   {"katsayi": 0.85},
            "İncirli":            {"katsayi": 0.92},
        },
        # Zeytinburnu ilçe ort: 585 TL/m²
        "Zeytinburnu": {
            "Yeşiltepe":          {"katsayi": 1.40},
            "Kazlıçeşme":         {"katsayi": 1.16},
            "Seyitnizam":         {"katsayi": 1.01},
            "Veliefendi":         {"katsayi": 0.89},
            "Merkezefendi":       {"katsayi": 0.72},
            "Beştelsiz":          {"katsayi": 0.95},
            "Sümer":              {"katsayi": 0.85},
            "Telsiz":             {"katsayi": 0.90},
            "Çırpıcı":            {"katsayi": 0.88},
            "Nuripaşa":           {"katsayi": 0.82},
            "Gökalp":             {"katsayi": 0.80},
        },
        # Bahçelievler ilçe ort: 393 TL/m²
        "Bahçelievler": {
            "Yenibosna":          {"katsayi": 1.40},
            "Yenibosna Merkez":   {"katsayi": 1.40},
            "Bahçelievler Mrk.":  {"katsayi": 1.09},
            "Şirinevler":         {"katsayi": 0.99},
            "Soğanlı":            {"katsayi": 0.87},
            "Kocasinan":          {"katsayi": 0.71},
            "Cumhuriyet(Bah)":    {"katsayi": 1.00},
            "Siyavuşpaşa":        {"katsayi": 0.92},
            "Hürriyet(Bah)":      {"katsayi": 0.95},
            "Zafer":              {"katsayi": 0.88},
            "Çobançeşme":         {"katsayi": 1.05},
            "Fevzi Çakmak(Bah)":  {"katsayi": 0.85},
        },
        # Güngören ilçe ort: 326 TL/m²
        "Güngören": {
            "Güngören Merkez":    {"katsayi": 1.41},
            "Tozkoparan":         {"katsayi": 1.20},
            "Mehmetçik":          {"katsayi": 1.01},
            "Sefaköy":            {"katsayi": 0.74},
            "Akıncılar":          {"katsayi": 0.85},
            "Gençosman":          {"katsayi": 0.90},
            "Güneştepe":          {"katsayi": 0.80},
            "Mareşal Çakmak":     {"katsayi": 0.88},
            "Haznedar":           {"katsayi": 0.92},
        },
        # Küçükçekmece ilçe ort: 367 TL/m²
        "Küçükçekmece": {
            "Atakent":            {"katsayi": 1.42},
            "Halkalı":            {"katsayi": 1.17},
            "Küçükçekmece Mrk.":  {"katsayi": 1.01},
            "İnönü":              {"katsayi": 0.84},
            "Tevfikbey":          {"katsayi": 0.72},
            "Cennet":             {"katsayi": 1.00},
            "Fatih(Küçük)":       {"katsayi": 0.90},
            "Yarımburgaz":        {"katsayi": 0.80},
            "Söğütlüçeşme":      {"katsayi": 0.88},
            "Beşyol":             {"katsayi": 0.95},
            "Kanarya":            {"katsayi": 0.82},
        },
    },

    "Alt-Orta Segment – Batı Avrupa": {
        # Bağcılar ilçe ort: 297 TL/m²
        "Bağcılar": {
            "Güneşli":            {"katsayi": 1.41},
            "Mahmutbey":          {"katsayi": 1.21},
            "Bağcılar Merkez":    {"katsayi": 1.01},
            "Kirazlı":            {"katsayi": 0.91},
            "Sefaköy(Bağ)":       {"katsayi": 0.72},
            "Yıldıztepe":         {"katsayi": 0.88},
            "Demirkapı":          {"katsayi": 0.85},
            "Fevzi Çakmak(Bağ)":  {"katsayi": 0.90},
            "Yenimahalle(Bağ)":   {"katsayi": 0.82},
            "İnönü(Bağ)":         {"katsayi": 0.85},
            "Kazım Karabekir":    {"katsayi": 0.80},
            "100. Yıl":           {"katsayi": 0.88},
            "Barbaros(Bağ)":      {"katsayi": 0.92},
        },
        # Avcılar ilçe ort: 307 TL/m²
        "Avcılar": {
            "Denizköşkler":       {"katsayi": 1.40},
            "Avcılar Merkez":     {"katsayi": 1.21},
            "Cihangir(Avc)":      {"katsayi": 1.01},
            "Ambarlı":            {"katsayi": 0.83},
            "Firuzköy":           {"katsayi": 0.72},
            "Yeşilkent":          {"katsayi": 0.90},
            "Mustafa Kemal Paşa": {"katsayi": 0.88},
            "Üniversite":         {"katsayi": 0.95},
            "Gümüşpala":          {"katsayi": 0.82},
        },
        # Beylikdüzü ilçe ort: 289 TL/m²
        "Beylikdüzü": {
            "Büyükşehir":         {"katsayi": 1.42},
            "Gürpınar":           {"katsayi": 1.25},
            "Beylikdüzü Mrk.":    {"katsayi": 1.00},
            "Adnan Kahveci":      {"katsayi": 0.87},
            "Cumhuriyet(Bey)":    {"katsayi": 0.73},
            "Yakuplu":            {"katsayi": 0.90},
            "Kavaklı":            {"katsayi": 0.85},
            "Barış":              {"katsayi": 0.88},
            "Dereağzı":           {"katsayi": 0.80},
            "Sahil":              {"katsayi": 1.10},
        },
        # Bayrampaşa ilçe ort: 326 TL/m²
        "Bayrampaşa": {
            "Yıldırım":           {"katsayi": 1.41},
            "Bayrampaşa Merkez":  {"katsayi": 1.10},
            "Muratpaşa":          {"katsayi": 1.01},
            "Altıntepsi":         {"katsayi": 0.72},
            "Kocatepe":           {"katsayi": 0.90},
            "İsmetpaşa":         {"katsayi": 0.85},
            "Vatan(Bay)":         {"katsayi": 0.88},
            "Cevatpaşa":          {"katsayi": 0.82},
        },
        # Gaziosmanpaşa ilçe ort: 294 TL/m²
        "Gaziosmanpaşa": {
            "Karadeniz":          {"katsayi": 1.41},
            "GOP Merkez":         {"katsayi": 1.12},
            "Fevzi Çakmak(GOP)":  {"katsayi": 1.00},
            "Karlıtepe":          {"katsayi": 0.85},
            "Yenidoğan(GOP)":     {"katsayi": 0.71},
            "Mevlana":            {"katsayi": 0.88},
            "Barbaros(GOP)":      {"katsayi": 0.90},
            "Bağlarbaşı(GOP)":    {"katsayi": 0.85},
            "Hürriyet(GOP)":      {"katsayi": 0.92},
            "Sarıgöl":            {"katsayi": 0.78},
            "Karayolları":        {"katsayi": 0.95},
            "Yıldıztabya":        {"katsayi": 0.82},
            "Pazariçi":           {"katsayi": 0.80},
        },
        # Başakşehir ilçe ort: 357 TL/m²
        "Başakşehir": {
            "Başakşehir 4.etap":  {"katsayi": 1.40},
            "Başakşehir 5.etap":  {"katsayi": 1.32},
            "Başakşehir Mrk.":    {"katsayi": 1.01},
            "Kayabaşı":           {"katsayi": 0.87},
            "İkitelli":           {"katsayi": 0.73},
            "Başak":              {"katsayi": 1.05},
            "Güvercintepe":       {"katsayi": 0.80},
            "Ziya Gökalp(Başak)": {"katsayi": 0.90},
            "Bahçeşehir 1.kısım": {"katsayi": 1.25},
            "Bahçeşehir 2.kısım": {"katsayi": 1.20},
            "Bahçeşehir":         {"katsayi": 1.22},
        },
        # Esenyurt ilçe ort: 228 TL/m²
        "Esenyurt": {
            "Esenyurt Merkez":    {"katsayi": 1.40},
            "Fatih Mah.(Esen)":   {"katsayi": 1.14},
            "Pınar":              {"katsayi": 1.01},
            "Saadetdere":         {"katsayi": 0.88},
            "Mehterçeşme":        {"katsayi": 0.72},
            "Barbaros Hayrettin":  {"katsayi": 1.00},
            "Barbaros Hayrettin Paşa": {"katsayi": 1.00},
            "Yenikent":           {"katsayi": 0.95},
            "Namık Kemal(Esen)":  {"katsayi": 0.90},
            "Ardıçlı":            {"katsayi": 0.85},
            "İncirtepe":          {"katsayi": 0.82},
            "İnönü(Esen)":        {"katsayi": 0.88},
            "Kıraç":              {"katsayi": 0.80},
        },
        # Büyükçekmece ilçe ort: 282 TL/m²
        "Büyükçekmece": {
            "Kumburgaz":          {"katsayi": 1.40},
            "Büyükçekmece Mrk.":  {"katsayi": 1.10},
            "Mimaroba":           {"katsayi": 1.01},
            "Gürpınar(Büy)":      {"katsayi": 0.85},
            "Tepecik":            {"katsayi": 0.73},
            "Alkent":             {"katsayi": 1.30},
            "Bahçelievler(Büy)":  {"katsayi": 0.90},
            "Fatih(Büy)":         {"katsayi": 0.85},
            "Pınartepe":          {"katsayi": 0.80},
        },
        # Esenler ilçe ort: 251 TL/m²
        "Esenler": {
            "Tuna":               {"katsayi": 1.41},
            "Esenler Merkez":     {"katsayi": 1.12},
            "Havaalanı":          {"katsayi": 1.00},
            "Nenehatun":          {"katsayi": 0.86},
            "Menderes":           {"katsayi": 0.72},
            "Oruçreis":           {"katsayi": 0.85},
            "Birlik":             {"katsayi": 0.82},
            "Kemer":              {"katsayi": 0.80},
            "Davutpaşa(Esen)":    {"katsayi": 0.90},
            "Fatih(Esen)":        {"katsayi": 0.88},
            "Kazım Karabekir(Es)":{"katsayi": 0.82},
        },
        # Sultangazi ilçe ort: 237 TL/m²
        "Sultangazi": {
            "Uğur Mumcu(Sul)":    {"katsayi": 1.41},
            "Sultangazi Merkez":  {"katsayi": 1.12},
            "Cebeci":             {"katsayi": 1.01},
            "Habibler":           {"katsayi": 0.84},
            "Gazi":               {"katsayi": 0.72},
            "50. Yıl":            {"katsayi": 0.88},
            "75. Yıl":            {"katsayi": 0.85},
            "Esentepe(Sul)":      {"katsayi": 0.82},
            "İsmetpaşa(Sul)":     {"katsayi": 0.80},
            "Cumhuriyet(Sul)":    {"katsayi": 0.90},
            "Zübeyde Hanım":      {"katsayi": 0.88},
            "Yayla":              {"katsayi": 0.78},
            "Malkoçoğlu":         {"katsayi": 0.82},
        },
        # Arnavutköy ilçe ort: 240 TL/m²
        "Arnavutköy": {
            "Hadımköy":           {"katsayi": 1.42},
            "Arnavutköy Merkez":  {"katsayi": 1.12},
            "Bolluca":            {"katsayi": 1.00},
            "Haraçcı":            {"katsayi": 0.83},
            "İmrahor":            {"katsayi": 0.73},
            "Taşoluk":            {"katsayi": 0.85},
            "Dursunköy":          {"katsayi": 0.80},
            "Yunus Emre(Arn)":    {"katsayi": 0.82},
        },
        # Silivri ilçe ort: 247 TL/m²
        "Silivri": {
            "Silivri Merkez":     {"katsayi": 1.42},
            "Selimpaşa":          {"katsayi": 1.17},
            "Silivri Çiftlikköy": {"katsayi": 1.01},
            "Fener(Sil)":         {"katsayi": 0.85},
            "Ortaköy(Sil)":       {"katsayi": 0.73},
            "Gümüşyaka":          {"katsayi": 0.90},
            "Alipaşa":            {"katsayi": 0.82},
            "Piri Mehmet Paşa":   {"katsayi": 0.88},
        },
        # Çatalca ilçe ort: 294 TL/m²
        "Çatalca": {
            "Çatalca Merkez":     {"katsayi": 1.41},
            "Ferhatpaşa(Çat)":    {"katsayi": 1.17},
            "Kaleiçi":            {"katsayi": 1.00},
            "Karacaköy":          {"katsayi": 0.83},
            "Elbasan":            {"katsayi": 0.73},
        },
    },

    # ── ANADOLU YAKASI ─────────────────────────────────────────────

    "Üst Segment – Boğaz (Anadolu)": {
        # Üsküdar ilçe ort: 425 TL/m²
        "Üsküdar": {
            "Çengelköy":          {"katsayi": 1.55},
            "Kuzguncuk":          {"katsayi": 1.44},
            "Beylerbeyi":         {"katsayi": 1.32},
            "Burhaniye":          {"katsayi": 1.28},
            "Kandilli":           {"katsayi": 1.25},
            "Acıbadem(Üsk)":      {"katsayi": 1.20},
            "Üsküdar Merkez":     {"katsayi": 1.00},
            "Bağlarbaşı":         {"katsayi": 0.92},
            "Ümraniye(Üsk)":      {"katsayi": 0.73},
            "Sultantepe":         {"katsayi": 0.95},
            "Altunizade":         {"katsayi": 1.15},
            "Bulgurlu":           {"katsayi": 0.88},
            "Bahçelievler(Üsk)":  {"katsayi": 0.90},
            "Ferah":              {"katsayi": 0.85},
            "Ünalan":             {"katsayi": 0.92},
            "Murat Reis":         {"katsayi": 0.95},
            "Selimiye":           {"katsayi": 1.00},
            "Salacak":            {"katsayi": 1.18},
            "Aziz Mahmut Hüdayi": {"katsayi": 1.00},
            "Cumhuriyet(Üsk)":    {"katsayi": 0.92},
        },
        # Beykoz ilçe ort: 356 TL/m²
        "Beykoz": {
            "Anadoluhisarı":      {"katsayi": 1.54},
            "Kavacık":            {"katsayi": 1.32},
            "Beykoz Merkez":      {"katsayi": 1.01},
            "Paşabahçe":          {"katsayi": 0.87},
            "Çubuklu":            {"katsayi": 0.73},
            "Anadolu Kavağı":     {"katsayi": 0.80},
            "Gümüşsuyu(Bey)":     {"katsayi": 0.90},
            "Yalıköy":            {"katsayi": 0.85},
            "Riva":               {"katsayi": 0.82},
            "Acarkent":           {"katsayi": 1.15},
        },
        # Adalar ilçe ort: 547 TL/m²
        "Adalar": {
            "Büyükada":           {"katsayi": 1.41},
            "Heybeliada":         {"katsayi": 1.17},
            "Burgazada":          {"katsayi": 1.01},
            "Kınalıada":          {"katsayi": 0.86},
            "Adalar Merkez":      {"katsayi": 0.73},
        },
    },

    "Üst-Orta Segment – Anadolu Merkez": {
        # Kadıköy ilçe ort: 651 TL/m²
        "Kadıköy": {
            "Moda":               {"katsayi": 1.55},
            "Fenerbahçe":         {"katsayi": 1.43},
            "Bağdat Caddesi":     {"katsayi": 1.35},
            "Caddebostan":        {"katsayi": 1.27},
            "Suadiye":            {"katsayi": 1.25},
            "Erenköy":            {"katsayi": 1.15},
            "Acıbadem(Kad)":      {"katsayi": 1.04},
            "Göztepe":            {"katsayi": 1.00},
            "Kozyatağı":          {"katsayi": 0.89},
            "Kadıköy Merkez":     {"katsayi": 0.83},
            "Bostancı":           {"katsayi": 0.72},
            "Caferağa":           {"katsayi": 1.10},
            "Osmanağa":           {"katsayi": 1.05},
            "Rasimpaşa":          {"katsayi": 1.00},
            "Yeldeğirmeni":       {"katsayi": 0.95},
            "Fikirtepe":          {"katsayi": 0.85},
            "Hasanpaşa(Kad)":     {"katsayi": 0.92},
            "Sahrayıcedit":       {"katsayi": 0.88},
            "Merdivenköy":        {"katsayi": 0.85},
            "Zühtüpaşa":          {"katsayi": 0.90},
            "İçerenköy(Kad)":     {"katsayi": 0.88},
            "Dumlupınar":         {"katsayi": 0.82},
        },
        # Ataşehir ilçe ort: 460 TL/m²
        "Ataşehir": {
            "İçerenköy":          {"katsayi": 1.41},
            "Barbaros":           {"katsayi": 1.28},
            "Ataşehir Merkez":    {"katsayi": 1.13},
            "Küçükbakkalköy":     {"katsayi": 1.00},
            "Kayışdağı":          {"katsayi": 0.87},
            "Ferhatpaşa":         {"katsayi": 0.73},
            "Yeni Çamlıca":       {"katsayi": 1.05},
            "Esatpaşa":           {"katsayi": 0.95},
            "Mimar Sinan(Ata)":   {"katsayi": 0.90},
            "Mustafa Kemal(Ata)": {"katsayi": 0.88},
            "Yenişehir(Ata)":     {"katsayi": 0.92},
            "Atatürk(Ata)":       {"katsayi": 0.85},
        },
        # Maltepe ilçe ort: 440 TL/m²
        "Maltepe": {
            "Cevizli":            {"katsayi": 1.41},
            "Bağlarbaşı(Mal)":    {"katsayi": 1.27},
            "Maltepe Merkez":     {"katsayi": 1.11},
            "Altayçeşme":         {"katsayi": 1.00},
            "Büyükbakkalköy":     {"katsayi": 0.84},
            "Aydınevler":         {"katsayi": 0.73},
            "Zümrütevler":        {"katsayi": 0.90},
            "Feyzullah":          {"katsayi": 0.85},
            "Gülsuyu":            {"katsayi": 0.80},
            "Gülensu":            {"katsayi": 0.78},
            "Başıbüyük":          {"katsayi": 0.75},
            "İdealtepe":          {"katsayi": 0.95},
            "Girne":              {"katsayi": 0.88},
            "Fındıklı(Mal)":      {"katsayi": 0.82},
        },
    },

    "Orta Segment – Anadolu Orta Kuşak": {
        # Kartal ilçe ort: 413 TL/m²
        "Kartal": {
            "Kordonboyu":         {"katsayi": 1.40},
            "Uğur Mumcu(Kar)":    {"katsayi": 1.21},
            "Kartal Merkez":      {"katsayi": 1.00},
            "Yakacık":            {"katsayi": 0.90},
            "Petrol İş":          {"katsayi": 0.73},
            "Soğanlık":           {"katsayi": 0.85},
            "Topselvi":           {"katsayi": 0.88},
            "Esentepe(Kar)":      {"katsayi": 0.82},
            "Hürriyet(Kar)":      {"katsayi": 0.80},
            "Atalar":             {"katsayi": 0.92},
            "Cevizli(Kar)":       {"katsayi": 0.95},
            "Karlıktepe":         {"katsayi": 0.78},
            "Orhantepe":          {"katsayi": 0.85},
            "Cumhuriyet(Kar)":    {"katsayi": 0.88},
        },
        # Ümraniye ilçe ort: 374 TL/m²
        "Ümraniye": {
            "Site":               {"katsayi": 1.42},
            "Namık Kemal":        {"katsayi": 1.23},
            "Ümraniye Merkez":    {"katsayi": 1.00},
            "Dudullu":            {"katsayi": 0.88},
            "Çakmak":             {"katsayi": 0.76},
            "Alemdağ":            {"katsayi": 0.72},
            "Atatürk(Ümr)":       {"katsayi": 0.90},
            "Hekimbaşı":          {"katsayi": 0.85},
            "İstiklal(Ümr)":      {"katsayi": 0.88},
            "Tantavi":            {"katsayi": 0.82},
            "Esenevler":          {"katsayi": 0.80},
            "Ihlamurkuyu":        {"katsayi": 0.85},
            "Armağanevler":       {"katsayi": 0.92},
            "Elmalıkent":         {"katsayi": 0.95},
            "Aşağı Dudullu":      {"katsayi": 0.85},
            "Yukarı Dudullu":     {"katsayi": 0.82},
        },
        # Çekmeköy ilçe ort: 364 TL/m²
        "Çekmeköy": {
            "Çekmeköy Merkez":    {"katsayi": 1.40},
            "Taşdelen":           {"katsayi": 1.24},
            "Nişantepe":          {"katsayi": 1.00},
            "Mehmet Akif(Çek)":   {"katsayi": 0.85},
            "Ömerli":             {"katsayi": 0.73},
            "Alemdağ(Çek)":       {"katsayi": 0.80},
            "Hamidiye(Çek)":      {"katsayi": 0.82},
            "Mimar Sinan(Çek)":   {"katsayi": 0.88},
            "Cumhuriyet(Çek)":    {"katsayi": 0.90},
        },
        # Pendik ilçe ort: 330 TL/m²
        "Pendik": {
            "İçmeler(Pen)":       {"katsayi": 1.42},
            "Yenişehir(Pen)":     {"katsayi": 1.24},
            "Kaynarca":           {"katsayi": 1.12},
            "Pendik Merkez":      {"katsayi": 1.00},
            "Kurtköy":            {"katsayi": 0.85},
            "Dolayoba":           {"katsayi": 0.73},
            "Çamlık":             {"katsayi": 0.92},
            "Velibaba":           {"katsayi": 0.88},
            "Güllü Bağlar":       {"katsayi": 0.80},
            "Esenler(Pen)":       {"katsayi": 0.82},
            "Bahçelievler(Pen)":  {"katsayi": 0.85},
            "Dumlupınar(Pen)":    {"katsayi": 0.78},
            "Batı":               {"katsayi": 0.90},
            "Kavakpınar":         {"katsayi": 0.85},
            "Sapanbağları":       {"katsayi": 0.82},
            "Ertuğrul Gazi":      {"katsayi": 0.80},
            "Yayalar":            {"katsayi": 0.78},
            "Ahmet Yesevi":       {"katsayi": 0.82},
            "Sülüntepe":          {"katsayi": 0.90},
        },
    },

    "Alt-Orta Segment – Anadolu Dış Kuşak": {
        # Tuzla ilçe ort: 322 TL/m²
        "Tuzla": {
            "İçmeler(Tuz)":       {"katsayi": 1.41},
            "Aydıntepe":          {"katsayi": 1.21},
            "Tuzla Merkez":       {"katsayi": 1.01},
            "Aydınlı":            {"katsayi": 0.87},
            "Mimar Sinan":        {"katsayi": 0.73},
            "Postane":            {"katsayi": 0.90},
            "Orhanlı":            {"katsayi": 0.82},
            "Şifa":               {"katsayi": 0.88},
            "Evliya Çelebi(Tuz)": {"katsayi": 0.85},
            "Yayla(Tuz)":         {"katsayi": 0.80},
        },
        # Sultanbeyli ilçe ort: 262 TL/m²
        "Sultanbeyli": {
            "Mehmet Akif(Sul)":   {"katsayi": 1.41},
            "Sultanbeyli Mrk.":   {"katsayi": 1.15},
            "Hasanpaşa(Sul)":     {"katsayi": 1.01},
            "Battalgazi":         {"katsayi": 0.88},
            "Fatih(Sul)":         {"katsayi": 0.73},
            "Akşemsettin":        {"katsayi": 0.90},
            "Orhangazi":          {"katsayi": 0.85},
            "Yavuz Selim(Sul)":   {"katsayi": 0.82},
            "Necip Fazıl":        {"katsayi": 0.88},
            "Turgut Reis":        {"katsayi": 0.80},
            "Abdurrahman Gazi":   {"katsayi": 0.85},
            "Mimar Sinan(Sul)":   {"katsayi": 0.78},
            "Hamidiye(Sul)":      {"katsayi": 0.82},
        },
        # Sancaktepe ilçe ort: 294 TL/m²
        "Sancaktepe": {
            "Samandıra":          {"katsayi": 1.41},
            "Sancaktepe Mrk.":    {"katsayi": 1.17},
            "Yenidoğan(San)":     {"katsayi": 1.00},
            "Eyüp Sultan(San)":   {"katsayi": 0.87},
            "Sarıgazi":           {"katsayi": 0.73},
            "İnönü(San)":         {"katsayi": 0.85},
            "Fatih(San)":         {"katsayi": 0.88},
            "Abdurrahmanpaşa":    {"katsayi": 0.82},
            "Osmangazi":          {"katsayi": 0.80},
            "Meclis":             {"katsayi": 0.85},
            "Emek":               {"katsayi": 0.78},
            "Paşaköy":            {"katsayi": 0.82},
            "Atatürk(San)":       {"katsayi": 0.88},
        },
        # Şile ilçe ort: 375 TL/m²
        "Şile": {
            "Şile Merkez":        {"katsayi": 1.41},
            "Ağva":               {"katsayi": 1.17},
            "Kumbaba":            {"katsayi": 1.00},
            "Doğancılı":          {"katsayi": 0.84},
            "Üvezli":             {"katsayi": 0.73},
            "Balibey":            {"katsayi": 0.90},
            "Sahilköy":           {"katsayi": 0.85},
            "Ağlayankaya":        {"katsayi": 0.88},
            "Yeniköy(Şile)":      {"katsayi": 0.82},
        },
    }
}

# ──────────────────────────────────────────────────────────────────
# İLÇE İSTATİSTİK TABLOSU
# Kaynak: Endeksa.com Mart 2026
# m2_kira        – ortalama kira TL/m²
# ort_deger      – satılık ortalama m² fiyatı (TL)
# amortisman_yil – amortisman süresi (yıl)
# getiri         – yıllık kira getirisi (%)
# yillik_degisim – yıllık fiyat değişimi (%)
# ──────────────────────────────────────────────────────────────────
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
    "üst":      {"katsayi": 1.10},
    "üst-orta": {"katsayi": 1.00},
    "orta":     {"katsayi": 0.95},
    "alt-orta": {"katsayi": 0.85},
    "alt":      {"katsayi": 0.75},
}

# ── Oda → m² aralıkları (simulate_metrekare için) ────────────────
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

# ── Referans m² (simulate_fiyat için — m² yoksa sabit referans) ──
REF_M2 = {
    "1+0": 35, "1+1": 60, "2+1": 90, "2+2": 100,
    "3+1": 130, "4+1": 180, "4+2": 210,
    "5+1": 250, "5+2": 280, "6+1": 350,
}


# ──────────────────────────────────────────────────────────────────
# Yardımcı fonksiyonlar
# ──────────────────────────────────────────────────────────────────

def is_empty(val) -> bool:
    """Return True if val is None, empty string, or the literal string 'nan'/'NaN'."""
    if val is None:
        return True
    s = str(val).strip()
    return s == "" or s.lower() == "nan"

def hesapla_m2_fiyat(ilce: str, katsayi: float) -> tuple[float, float]:
    """İlçe ortalaması × katsayı ile m2_fiyat ve std hesapla. std = m2_fiyat × 0.08"""
    ilce_ort = ILCE_ORT.get(ilce, 370)  # fallback: İstanbul genel ort
    katsayi = max(MIN_KATSAYI, min(MAX_KATSAYI, katsayi))  # soft clamp
    m2_fiyat = ilce_ort * katsayi
    std = m2_fiyat * 0.08
    return m2_fiyat, std


def _ilce_from_konum(konum: str) -> str:
    """Konum stringinden ilçe adını çıkar (ILCE_ORT'daki anahtarlarla eşleştir)."""
    kl = konum.lower()
    # Uzun isimlerden kısaya sırala (ör. "Gaziosmanpaşa" > "Fatih")
    for ilce in sorted(ILCE_ORT.keys(), key=len, reverse=True):
        if ilce.lower() in kl:
            return ilce
    return ""


def lookup_mahalle(konum: str) -> tuple[dict | None, str, str]:
    """
    Konum string'inden mahalle düzeyinde fiyat verisi arar.
    Returns (fiyat_dict, segment_adi, ilce_adi) — bulunamazsa (None, "", "").

    Öncelik:
      1. MAHALLELER dict'inde mahalle ismi eşleşmesi (longest-match)
      2. İlçe adı eşleşmesi → katsayi=1.00 (ilçe ortalaması)
    """
    kl = konum.lower()
    best_data = None
    best_segment = ""
    best_ilce = ""
    best_len = 0

    for segment, ilceler in MAHALLELER.items():
        for ilce, mahalleler in ilceler.items():
            for mahalle, data in mahalleler.items():
                key = mahalle.lower()
                if key in kl and len(key) > best_len:
                    best_data = data
                    best_segment = segment
                    best_ilce = ilce
                    best_len = len(key)

    # Mahalle eşleşti
    if best_data:
        return best_data, best_segment, best_ilce

    # Mahalle eşleşmedi → ilçe adı eşleştir, katsayi=1.00 ver
    ilce = _ilce_from_konum(konum)
    if ilce:
        # İlçenin hangi segmentte olduğunu bul
        for segment, ilceler in MAHALLELER.items():
            if ilce in ilceler:
                return {"katsayi": 1.00}, segment, ilce
        # MAHALLELER'de ilçe yoksa bile ILCE_ORT'da varsa kullan
        return {"katsayi": 1.00}, "", ilce

    return None, "", ""


def get_tier(konum: str) -> str:
    """
    Konum'dan segment adını bulup tier döndürür.
    Mahalle eşleşmesi yoksa ilçe adına göre tahmin eder.
    """
    _, segment, _ = lookup_mahalle(konum)
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


def simulate_fiyat(baslik: str, oda: str, konum: str, metrekare: str = "") -> str:
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

    # 2. Lokasyon bazlı birim fiyat (EN BASKIN FAKTÖR)
    mahalle_data, segment, ilce_adi = lookup_mahalle(konum)
    tier = get_tier(konum)

    if mahalle_data:
        katsayi = mahalle_data["katsayi"]
        m2_birim, std = hesapla_m2_fiyat(ilce_adi, katsayi)
    else:
        fb = TIER_FALLBACK.get(tier, TIER_FALLBACK["orta"])
        m2_birim, std = hesapla_m2_fiyat("", fb["katsayi"])

    # 3. Kullanılacak m² belirleme (öncelik: gerçek m² > referans m²)
    kullanilan_m2 = None

    # 3a. Parametre olarak gelen gerçek m² (CSV'den)
    if metrekare:
        try:
            val = int(float(metrekare))
            if 20 <= val <= 2000:
                kullanilan_m2 = val
        except (ValueError, TypeError):
            pass

    # 3b. Gerçek m² yoksa, oda tipine göre REFERANS m² kullan
    if kullanilan_m2 is None:
        kullanilan_m2 = REF_M2.get(oda, 90)

    # 4. Villa çarpanı
    villa_carpan = 1.0
    if is_villa_like(baslik):
        villa_carpan = 1.4

    # 5. Noise (birim fiyata, %8 std)
    m2_birim_noisy = random.gauss(m2_birim, std)

    # 6. Fiyat hesapla (lokasyon baskın)
    fiyat = int(kullanilan_m2 * m2_birim_noisy * villa_carpan)

    # 7. Minimum fiyat: İstanbul'da 20.000 TL altı kira yok
    fiyat = max(20000, fiyat)
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

# ──────────────────────────────────────────────────────────────────
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

    # Metrekare — önce simüle et (gerekiyorsa)
    if is_empty(row.get("Metrekare")):
        row["Metrekare"] = simulate_metrekare(baslik, oda)

    # Kat
    if is_empty(row.get("Kat")):
        row["Kat"] = simulate_kat(baslik)

    # Fiyat — her satır için yeniden simüle et (kaynak verideki fiyatlar güvenilmez)
    # Gerçek metrekare varsa onu kullan
    row["Fiyat"] = simulate_fiyat(baslik, oda, konum, row.get("Metrekare", ""))

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