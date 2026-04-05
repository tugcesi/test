"""
Hepsiemlak.com Web Scraper
Mevcut CSV'deki 9597 ilana ait eksik verileri (Fiyat, Metrekare, Kat,
Banyo Sayısı, Yapı Yaşı, Eşya Durumu) çeker ve zenginleştirilmiş CSV'yi kaydeder.

Kullanım:
    pip install -r requirements.txt
    python scraper.py

Çıktı:
    istanbul_kiralik_complete_scraped.csv
"""

import csv
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ─── Sabitler ────────────────────────────────────────────────────────────────

INPUT_CSV = "istanbul_kiralik_complete.csv"
OUTPUT_CSV = "istanbul_kiralik_complete_scraped.csv"
CHECKPOINT_FILE = "scraper_checkpoint.json"
FAILED_LOG = "scraper_failed.csv"

CHECKPOINT_INTERVAL = 100   # Her N ilandan sonra kaydet
MIN_DELAY = 1.0             # saniye
MAX_DELAY = 3.0             # saniye
MAX_RETRIES = 3             # başarısız istekler için
RETRY_BACKOFF = 5           # saniye (retry'larda eklenir)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

# ─── Yardımcı Fonksiyonlar ───────────────────────────────────────────────────


def build_headers() -> dict:
    """Rastgele User-Agent ile gerçekçi browser başlıkları oluştur."""
    ua = random.choice(USER_AGENTS)
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }


def clean_number(text: str) -> str:
    """Sayısal değerden gereksiz karakterleri temizle."""
    if not text:
        return ""
    # Türkçe binlik ayraçlarını ve gereksiz boşlukları kaldır
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def parse_listing_page(html: str, url: str) -> dict:
    """
    Hepsiemlak ilan sayfasından verileri ayrıştır.
    Dönen dict anahtarları: Fiyat, Metrekare, Kat, Banyo Sayısı, Yapı Yaşı, Eşya
    """
    result = {
        "Fiyat": "",
        "Metrekare": "",
        "Kat": "",
        "Banyo Sayısı": "",
        "Yapı Yaşı": "",
        "Eşya": "",
        "Isıtma": "",
    }

    soup = BeautifulSoup(html, "html.parser")

    # ── 1. JSON-LD / __NEXT_DATA__ / window.__data__ içinden dene ──────────
    # Hepsiemlak genellikle Next.js kullanır; sayfa verileri __NEXT_DATA__'da
    next_data_tag = soup.find("script", id="__NEXT_DATA__")
    if next_data_tag and next_data_tag.string:
        try:
            data = json.loads(next_data_tag.string)
            props = data.get("props", {}).get("pageProps", {})
            listing = (
                props.get("listing")
                or props.get("listingDetail")
                or props.get("detail")
                or {}
            )
            if listing:
                _extract_from_json(listing, result)
                if any(result.values()):
                    return result
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # ── 2. JSON-LD (schema.org) ─────────────────────────────────────────────
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                for item in data:
                    _extract_from_jsonld(item, result)
            else:
                _extract_from_jsonld(data, result)
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

    # ── 3. HTML tablosundan / özellik listesinden çek ───────────────────────
    _extract_from_html(soup, result)

    return result


def _extract_from_json(listing: dict, result: dict) -> None:
    """Next.js listing objesinden alanları doldur."""
    field_map = {
        "price": "Fiyat",
        "priceText": "Fiyat",
        "squareMeters": "Metrekare",
        "grossSquareMeters": "Metrekare",
        "netSquareMeters": "Metrekare",
        "floor": "Kat",
        "floorText": "Kat",
        "bathroomCount": "Banyo Sayısı",
        "buildingAge": "Yapı Yaşı",
        "buildingAgeText": "Yapı Yaşı",
        "isFurnished": "Eşya",
        "furnishingText": "Eşya",
        "heatingType": "Isıtma",
        "heatingTypeText": "Isıtma",
    }
    for src, dst in field_map.items():
        val = listing.get(src)
        if val is not None and str(val).strip():
            if not result[dst]:
                result[dst] = clean_number(str(val))

    # Nested attributes
    attrs = listing.get("attributes") or listing.get("specs") or []
    if isinstance(attrs, list):
        for attr in attrs:
            label = str(attr.get("label", "")).lower()
            value = str(attr.get("value", "")).strip()
            if not value:
                continue
            if "m²" in label or "metrekare" in label or "brüt" in label or "net" in label:
                result["Metrekare"] = result["Metrekare"] or value
            elif "kat" in label:
                result["Kat"] = result["Kat"] or value
            elif "banyo" in label:
                result["Banyo Sayısı"] = result["Banyo Sayısı"] or value
            elif "yapı yaşı" in label or "bina yaşı" in label:
                result["Yapı Yaşı"] = result["Yapı Yaşı"] or value
            elif "eşya" in label or "mobilya" in label:
                result["Eşya"] = result["Eşya"] or value
            elif "ısıtma" in label:
                result["Isıtma"] = result["Isıtma"] or value


def _extract_from_jsonld(data: dict, result: dict) -> None:
    """schema.org JSON-LD objesinden değer çek."""
    if not isinstance(data, dict):
        return
    offers = data.get("offers", {})
    if isinstance(offers, dict):
        price = offers.get("price") or offers.get("priceSpecification", {}).get("price")
        currency = offers.get("priceCurrency", "TRY")
        if price and not result["Fiyat"]:
            result["Fiyat"] = f"{price} {currency}"

    floor_size = data.get("floorSize", {})
    if isinstance(floor_size, dict) and floor_size.get("value"):
        result["Metrekare"] = result["Metrekare"] or str(floor_size["value"])

    additional = data.get("additionalProperty", [])
    if isinstance(additional, list):
        for prop in additional:
            name = str(prop.get("name", "")).lower()
            value = str(prop.get("value", "")).strip()
            if not value:
                continue
            if "kat" in name:
                result["Kat"] = result["Kat"] or value
            elif "banyo" in name:
                result["Banyo Sayısı"] = result["Banyo Sayısı"] or value
            elif "yaş" in name:
                result["Yapı Yaşı"] = result["Yapı Yaşı"] or value
            elif "eşya" in name or "mobilya" in name:
                result["Eşya"] = result["Eşya"] or value
            elif "ısıtma" in name:
                result["Isıtma"] = result["Isıtma"] or value


def _extract_from_html(soup: BeautifulSoup, result: dict) -> None:
    """HTML DOM'dan özellik değerlerini çek (birden fazla selector dener)."""

    # Fiyat
    if not result["Fiyat"]:
        for sel in [
            ("span", {"class": re.compile(r"price|fiyat", re.I)}),
            ("div", {"class": re.compile(r"price|fiyat", re.I)}),
            ("p", {"class": re.compile(r"price|fiyat", re.I)}),
            ("strong", {"class": re.compile(r"price|fiyat", re.I)}),
        ]:
            tag = soup.find(*sel)
            if tag and tag.get_text(strip=True):
                result["Fiyat"] = clean_number(tag.get_text(strip=True))
                break

    # Özellik tablosu / liste: Hepsiemlak "short-properties" ve
    # "property-features" gibi sınıflar kullanır
    feature_containers = soup.find_all(
        ["ul", "div", "table"],
        class_=re.compile(
            r"feature|ozellik|detail|specs|property|short-prop|realty-features",
            re.I,
        ),
    )

    # Ayrıca genel dt/dd, li, tr ögeleri de tara
    all_items: list = []
    for container in feature_containers:
        all_items.extend(container.find_all(["li", "tr", "dt", "dd", "span", "div"]))

    # Sayfadaki tüm li ve dt/dd çiftlerini de tara (genel)
    all_items.extend(soup.find_all(["li", "dt", "dd"]))

    # Tekrar eden elemanlar için set kullan
    seen = set()
    for item in all_items:
        item_id = id(item)
        if item_id in seen:
            continue
        seen.add(item_id)

        text = item.get_text(" ", strip=True)
        _try_assign_from_text(text, result)

    # Fiyat için ek deneme
    if not result["Fiyat"]:
        # data-* attribute içeren etiketler
        for tag in soup.find_all(attrs={"data-price": True}):
            result["Fiyat"] = clean_number(tag["data-price"])
            break


def _try_assign_from_text(text: str, result: dict) -> None:
    """Metin içinde anahtar kelime varsa ilgili alana ata."""
    lower = text.lower()

    patterns = {
        "Metrekare": [r"(\d[\d\.,]*)\s*m[²2]", r"metrekare\s*[:\-]?\s*(\d[\d\.,]*)"],
        "Kat": [r"(?:bulunduğu\s+)?kat\s*[:\-]?\s*([\w\d\+\/\-]+)"],
        "Banyo Sayısı": [r"banyo\s*[:\-]?\s*(\d+)"],
        "Yapı Yaşı": [r"yapı\s+yaşı\s*[:\-]?\s*([\w\d\-\+]+)", r"bina\s+yaşı\s*[:\-]?\s*([\w\d\-\+]+)"],
        "Eşya": [r"eşya\s*[:\-]?\s*(eşyalı|eşyasız)", r"(eşyalı|eşyasız)"],
        "Isıtma": [r"[iı]s[iı]tma\s*[:\-]?\s*(.+)"],
    }

    for field, pats in patterns.items():
        if result[field]:
            continue
        for pat in pats:
            m = re.search(pat, lower)
            if m:
                result[field] = clean_number(m.group(1))
                break

    # Fiyat: TL/₺ içeren metinler
    if not result["Fiyat"]:
        m = re.search(r"([\d\.\, ]+)\s*(?:tl|₺|try)", lower)
        if m:
            result["Fiyat"] = clean_number(m.group(0))


# ─── Checkpoint Yönetimi ─────────────────────────────────────────────────────


def load_checkpoint() -> dict:
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_index": 0, "results": {}}


def save_checkpoint(last_index: int, results: dict) -> None:
    tmp = CHECKPOINT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"last_index": last_index, "results": results}, f, ensure_ascii=False)
    os.replace(tmp, CHECKPOINT_FILE)


# ─── İlerleme Çubuğu ─────────────────────────────────────────────────────────


def progress_bar(current: int, total: int, success: int, fail: int, eta: str) -> None:
    width = 40
    pct = current / total if total else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    sys.stdout.write(
        f"\r[{bar}] {current}/{total} ({pct*100:.1f}%)  "
        f"✓{success} ✗{fail}  ETA:{eta}    "
    )
    sys.stdout.flush()


def format_eta(seconds: float) -> str:
    if seconds < 0 or seconds > 86400 * 2:
        return "--:--"
    return str(timedelta(seconds=int(seconds)))


# ─── Ana Scraper ──────────────────────────────────────────────────────────────


def scrape_listing(session: requests.Session, url: str) -> Optional[dict]:
    """
    Tek bir ilanı çek ve parse et.
    Başarısız olursa MAX_RETRIES kez yeniden dene.
    None döndürürse başarısız sayılır.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            headers = build_headers()
            # Referer olarak hepsiemlak ana sayfasını ekle
            headers["Referer"] = "https://www.hepsiemlak.com/"
            resp = session.get(url, headers=headers, timeout=20, allow_redirects=True)

            if resp.status_code == 200:
                return parse_listing_page(resp.text, url)
            elif resp.status_code in (429, 503):
                # Rate limited – uzun bekle
                wait = RETRY_BACKOFF * attempt + random.uniform(2, 5)
                time.sleep(wait)
                continue
            elif resp.status_code == 403:
                # Anti-bot – farklı header dene
                wait = RETRY_BACKOFF * attempt
                time.sleep(wait)
                continue
            elif resp.status_code == 404:
                return None  # Sayfa yok, retry etme
            else:
                time.sleep(RETRY_BACKOFF)
        except requests.exceptions.Timeout:
            time.sleep(RETRY_BACKOFF * attempt)
        except requests.exceptions.ConnectionError:
            time.sleep(RETRY_BACKOFF * attempt)
        except requests.exceptions.RequestException:
            time.sleep(RETRY_BACKOFF)

    return None


def main() -> None:
    print("=" * 60)
    print("  Hepsiemlak.com Web Scraper")
    print("=" * 60)
    print(f"  Giriş  : {INPUT_CSV}")
    print(f"  Çıkış  : {OUTPUT_CSV}")
    print(f"  Kontrol: {CHECKPOINT_FILE}")
    print("=" * 60)

    # CSV oku
    if not os.path.exists(INPUT_CSV):
        print(f"[HATA] {INPUT_CSV} bulunamadı!")
        sys.exit(1)

    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    total = len(rows)
    print(f"\n  Toplam ilan: {total}\n")

    # Checkpoint'i yükle
    ckpt = load_checkpoint()
    start_index = ckpt["last_index"]
    cached_results: dict = ckpt["results"]  # {url: {field: value}}

    if start_index > 0:
        print(f"  ▶ Checkpoint bulundu: {start_index}. ilandan devam ediliyor.\n")

    # Başarısız kayıt dosyası
    failed_file = open(FAILED_LOG, "a", newline="", encoding="utf-8")
    failed_writer = csv.writer(failed_file)
    if os.stat(FAILED_LOG).st_size == 0:
        failed_writer.writerow(["index", "url", "reason"])

    # HTTP Session (bağlantı havuzu)
    session = requests.Session()
    session.max_redirects = 5

    # Çıktı fieldnames – mevcut alanlara ek olarak yeni alanlar
    extra_fields = ["Fiyat", "Metrekare", "Kat", "Banyo Sayısı", "Yapı Yaşı", "Eşya", "Isıtma"]
    out_fields = list(fieldnames)
    for ef in extra_fields:
        if ef not in out_fields:
            out_fields.append(ef)

    # Çıktı CSV'yi aç (ekleme modunda değil, yeniden yaz)
    output_exists = os.path.exists(OUTPUT_CSV)
    out_file = open(OUTPUT_CSV, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(out_file, fieldnames=out_fields, extrasaction="ignore")
    writer.writeheader()

    success_count = 0
    fail_count = 0
    times: list = []
    start_time = time.time()

    try:
        for i, row in enumerate(rows):
            # Zaten işlenmiş satırları direkt yaz
            url = row.get("URL", "").strip()

            if i < start_index:
                # Checkpoint'ten önceki satırları cached_results'tan doldur
                if url in cached_results:
                    row.update(cached_results[url])
                    success_count += 1
                else:
                    fail_count += 1
                writer.writerow(row)
                continue

            # İlerleme çubuğu
            if times:
                avg_time = sum(times[-20:]) / len(times[-20:])
                remaining = (total - i) * avg_time
                eta = format_eta(remaining)
            else:
                eta = "--:--"
            progress_bar(i, total, success_count, fail_count, eta)

            if not url:
                fail_count += 1
                failed_writer.writerow([i, url, "URL yok"])
                writer.writerow(row)
                continue

            t0 = time.time()
            scraped = scrape_listing(session, url)
            elapsed = time.time() - t0
            times.append(elapsed)

            if scraped:
                # Sadece boş alanları doldur (var olanları üzerine yazma)
                for field, value in scraped.items():
                    if value and not row.get(field):
                        row[field] = value
                cached_results[url] = scraped
                success_count += 1
            else:
                fail_count += 1
                failed_writer.writerow([i, url, "Scrape başarısız"])

            writer.writerow(row)

            # Checkpoint kaydet
            if (i + 1) % CHECKPOINT_INTERVAL == 0:
                save_checkpoint(i + 1, cached_results)
                out_file.flush()
                failed_file.flush()

            # Rate limiting
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            time.sleep(delay)

    except KeyboardInterrupt:
        print("\n\n  ⚠ Kullanıcı tarafından durduruldu. İlerleme kaydediliyor...")
        save_checkpoint(i, cached_results)

    finally:
        out_file.flush()
        out_file.close()
        failed_file.close()
        session.close()

    # Son checkpoint
    save_checkpoint(total, cached_results)

    print()  # progress bar satırını bitir
    print()
    elapsed_total = time.time() - start_time
    print("=" * 60)
    print(f"  ✅ Tamamlandı!")
    print(f"  Toplam ilan     : {total}")
    print(f"  Başarılı        : {success_count}")
    print(f"  Başarısız       : {fail_count}")
    print(f"  Süre            : {format_eta(elapsed_total)}")
    print(f"  Çıktı dosyası   : {OUTPUT_CSV}")
    if fail_count > 0:
        print(f"  Başarısız log   : {FAILED_LOG}")
    print("=" * 60)


if __name__ == "__main__":
    main()
