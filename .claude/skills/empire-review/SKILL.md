---
name: empire-review
description: Провести еженедельный CEO Review в Empire OS — разбор прошлой недели, состояние портфеля и три результата новой недели со списком «не делать». Использовать в понедельник, при словах «ревью», «итоги недели», «план на неделю».
---

# CEO Review

Веди по [rituals/weekly-ceo-review.md](../../../rituals/weekly-ceo-review.md), пять частей,
ни одна не пропускается.

```bash
python3 tools/empire.py week
python3 tools/empire.py commitments --all
python3 tools/empire.py capacity
python3 tools/empire.py skills --bottlenecks
python3 tools/empire.py stuck
```

Обязательное:

- Незакрытый результат недели разбирается: не хватило времени / не та задача / избегали.
- CFO называет состояние каждого проекта вслух: **расход / актив / бизнес**.
- Продукт в `product-development` дольше двух недель при нуле разговоров с пользователями →
  CPO ставит вопрос «стоп development».
- Новая неделя: **ровно три результата**, каждый — завершённое состояние, а не деятельность.
  Список `not_doing` обязателен и содержит то, что реально хочется сделать.

```bash
python3 tools/empire.py week-plan --result "..." --result "..." --result "..." --not-doing "..."
python3 tools/empire.py capacity-set meal-planner=50 price-base=25 founder-skills=15 exploration=10
python3 tools/empire.py render
```

Закончи фиксацией: обещания → `commit-add`, решения → `decision-add` с условием возврата.
