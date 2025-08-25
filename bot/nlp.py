from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
COURSES_CSV = DATA_DIR / "courses.csv"

@dataclass
class Catalog:
    df: pd.DataFrame
    vectorizer: TfidfVectorizer
    matrix: np.ndarray  # TF-IDF матрица по полю 'name'

    @classmethod
    def load(cls) -> "Catalog":
        df = pd.read_csv(COURSES_CSV)
        df["name"] = df["name"].fillna("").astype(str)
        df["tags"] = df["tags"].fillna("").astype(str)
        corpus = (df["name"] + " " + df["tags"])
        vectorizer = TfidfVectorizer(ngram_range=(1,2), min_df=1)
        X = vectorizer.fit_transform(corpus)
        return cls(df=df, vectorizer=vectorizer, matrix=X)

    def search(self, query: str, program: str | None = None, topk: int = 5):
        qv = self.vectorizer.transform([query])
        sims = cosine_similarity(qv, self.matrix).ravel()
        idx = np.argsort(-sims)
        rows = []
        for i in idx[: topk * 3]:  # запас, вдруг программа отфильтрует
            row = self.df.iloc[i]
            if program and row["program"] != program:
                continue
            rows.append((float(sims[i]), row.to_dict()))
            if len(rows) >= topk:
                break
        return rows

def detect_intent(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["сравни", "чем отличается", "что лучше", "compare"]):
        return "compare"
    if any(k in t for k in ["план", "семестр", "curriculum", "учебный план"]):
        return "plan"
    if any(k in t for k in ["курс", "есть ли", "где изучают", "ищу", "поиск"]):
        return "find_course"
    if any(k in t for k in ["бэкграунд", "background", "я из", "мой опыт", "посовету", "рекоменд"]):
        return "recommend"
    # нерелевант
    if not any(k in t for k in ["ai", "програм", "курс", "магистр", "итмо", "план", "семестр", "поступ"]):
        return "offtopic"
    return "fallback"

def background_to_tags(text: str) -> list[str]:
    t = text.lower()
    tags = []
    mapping = {
        "математ": "math",
        "вероят": "math",
        "статист": "math",
        "программи": "coding",
        "python": "coding",
        "разработ": "coding",
        "data": "data",
        "аналит": "data",
        "ml": "ml",
        "машин": "ml",
        "cv": "cv",
        "зрени": "cv",
        "nlp": "nlp",
        "язык": "nlp",
        "product": "product",
        "менедж": "product",
    }
    for key, tag in mapping.items():
        if key in t:
            tags.append(tag)
    return sorted(set(tags)) or ["ml"]  # разумный дефолт

def recommend(df: pd.DataFrame, user_tags: Iterable[str], program: str | None = None, topk: int = 5):
    tags = set(user_tags)
    # вес за совпадение тегов
    def tag_score(s):
        course_tags = set(str(s).split(",") if isinstance(s, str) and "," in s else str(s).split())
        return len(tags & course_tags)

    work = df.copy()
    if program:
        work = work[work["program"] == program]
    work["tag_score"] = work["tags"].apply(tag_score)
    work["sem_prio"] = work["semester"].fillna(99).apply(lambda x: -int(x))  # раньше = выше
    work = work.sort_values(["tag_score", "sem_prio"], ascending=[False, True])
    return work.head(topk).to_dict(orient="records")
