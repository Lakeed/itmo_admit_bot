## ITMO Admit Bot

Бот помогает абитуриенту сравнить магистратуры `AI` и `AI Product` (ИТМО), найти курсы в учебном плане и получить рекомендации элективов под свой бэкграунд.

### Установка
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

### Структура
itmo-admit-bot/
├─ data/ (curricula.json, courses.csv)
├─ parser/ (parse_program.py)
├─ bot/
│  ├─ main.py
│  ├─ intents.py
│  ├─ nlp.py (TF-IDF, поиск, рекомендации)
│  └─ replies.py
├─ notebooks/ (EDA курсов)
├─ README.md (как запустить)
└─ requirements.txt