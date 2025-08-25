import json
import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

AI_URL = "https://abit.itmo.ru/program/master/ai"
AIP_URL = "https://abit.itmo.ru/program/master/ai_product"

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AdmitBot/1.0; +https://example.org)"
}

def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text

def extract_courses(html: str) -> list[dict]:
    """
    Структура сайтов может меняться; используем эвристики:
    - ищем таблицы и списки с курсами, вероятные колонки: название/семестр/тип/часы
    - если явной таблицы нет — собираем <li> и <a> с ключевыми словами
    """
    soup = BeautifulSoup(html, "html.parser")
    courses: list[dict] = []

    # 1) Попытка распарсить таблицы
    for table in soup.find_all(["table"]):
        headers = [th.get_text(strip=True).lower() for th in table.select("thead th")]
        for tr in table.select("tbody tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if not cells:
                continue
            name = cells[0]
            sem = None
            ctype = None
            hours = None
            for h, v in zip(headers[1:], cells[1:]):
                if "семестр" in h:
                    sem = re.findall(r"\d+", v)
                    sem = int(sem[0]) if sem else None
                if "тип" in h or "дисциплин" in h:
                    ctype = v
                if "час" in h or "зет" in h:
                    hours = v
            courses.append(dict(name=name, semester=sem, kind=ctype, hours=hours))
    if courses:
        return courses

    # 2) Списки
    for li in soup.find_all("li"):
        txt = li.get_text(" ", strip=True)
        if len(txt) < 5 or len(txt) > 150:
            continue
        if any(k in txt.lower() for k in ["курс", "анал", "машин", "данн", "product", "управл", "cv", "nlp", "ai"]):
            courses.append(dict(name=txt, semester=None, kind=None, hours=None))

    # 3) fallback — теги ссылок
    for a in soup.find_all("a"):
        txt = a.get_text(" ", strip=True)
        if 5 <= len(txt) <= 120 and re.search(r"[A-Za-zА-Яа-я]", txt or ""):
            if any(k in txt.lower() for k in ["курс", "машин", "данн", "нейрон", "product", "nlp", "vision"]):
                courses.append(dict(name=txt, semester=None, kind=None, hours=None))

    # dedup
    seen = set()
    uniq = []
    for c in courses:
        key = c["name"].lower()
        if key not in seen:
            uniq.append(c)
            seen.add(key)
    return uniq

def tag_course(name: str) -> list[str]:
    n = name.lower()
    tags = []
    rules = [
        (["nlp", "обработка текста", "язык", "language"], "nlp"),
        (["cv", "computer vision", "компьютерное зрение", "vision"], "cv"),
        (["ml", "машин", "machine learning"], "ml"),
        (["deep", "нейрон", "deep learning"], "dl"),
        (["product", "продукт", "менеджмент"], "product"),
        (["math", "математ", "статист", "вероят"], "math"),
        (["data", "данн", "аналит"], "data"),
        (["python", "программи"], "coding"),
    ]
    for keys, tag in rules:
        if any(k in n for k in keys):
            tags.append(tag)
    return sorted(set(tags))

def scrape_program(url: str, program_code: str) -> list[dict]:
    print(f"Fetching {program_code} ...")
    html = fetch(url)
    raw = extract_courses(html)
    out = []
    for r in raw:
        r["program"] = program_code
        r["tags"] = tag_course(r["name"])
        out.append(r)
    return out

def main():
    all_courses = []
    for url, code in [(AI_URL, "AI"), (AIP_URL, "AI_PRODUCT")]:
        try:
            all_courses += scrape_program(url, code)
            time.sleep(1.5)
        except Exception as e:
            print(f"WARNING: cannot parse {code}: {e}")

    if not all_courses:
        # На случай недоступности сайтов — минимальная заглушка
        all_courses = [
            {"name": "Machine Learning", "semester": 1, "kind": "обяз.", "hours": "4 з.е.", "program": "AI", "tags": ["ml"]},
            {"name": "Deep Learning", "semester": 2, "kind": "электив", "hours": "3 з.е.", "program": "AI", "tags": ["dl"]},
            {"name": "Computer Vision", "semester": 2, "kind": "электив", "hours": "3 з.е.", "program": "AI", "tags": ["cv"]},
            {"name": "NLP", "semester": 2, "kind": "электив", "hours": "3 з.е.", "program": "AI_PRODUCT", "tags": ["nlp"]},
            {"name": "Product Management for AI", "semester": 1, "kind": "обяз.", "hours": "4 з.е.", "program": "AI_PRODUCT", "tags": ["product"]},
        ]

    # сохранение
    df = pd.DataFrame(all_courses)
    df.to_csv(DATA_DIR / "courses.csv", index=False)

    by_program = {
        prog: df[df["program"] == prog].to_dict(orient="records")
        for prog in df["program"].unique()
    }
    with open(DATA_DIR / "curricula.json", "w", encoding="utf-8") as f:
        json.dump(by_program, f, ensure_ascii=False, indent=2)

    print(f"Saved: {DATA_DIR/'courses.csv'} and {DATA_DIR/'curricula.json'}")

if __name__ == "__main__":
    main()
