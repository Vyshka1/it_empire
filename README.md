# Empire OS

Персональный стратег и операционный директор для одного человека, строящего IT-империю.

Не учитель программирования. Его вопрос не «что такое REST API», а «что ты построила за
неделю, что из этого создаёт актив и где ты застряла».

```
идеи → продукты → работающие активы → бизнес
```

Полная концепция: [CONCEPT.md](CONCEPT.md).

## Как это выглядит утром

```
$ python3 tools/empire.py status

EMPIRE OS · 2026-09-16 · 2026-W38
  ⚠ Vision не заполнен. Портфель без цели — это набор пет-проектов.

НЕДЕЛЯ 2026-W38
  · #1 [meal-planner] Закончить архитектурную стабилизацию WeekPlan
  · #2 [price-base] Провести discovery и определить MVP
  · #3 [founder] Разобраться с deployment, чтобы контролировать выкладку

  НЕ ДЕЛАТЬ:
    — Новый дизайн Meal Planner
    — Новые рецепты
    — Signal — до окончания discovery по Price Base

ПОРТФЕЛЬ
  Meal Planner            product-development   пользователей не видел никогда
  Корпоративная база цен  idea                  пользователей не видел никогда
  Система для Signal      idea                  пользователей не видел никогда

  ⚠ Ни одним продуктом портфеля никто не пользуется. Активов пока ноль.

BOTTLENECKS
  PRODUCT/product-discovery — Три проекта, ноль разговоров с пользователями
  PRODUCT/customer-research — Price Base стоит на discovery
```

## Первый запуск

1. Провести Vision-сессию: [`rituals/vision-session.md`](rituals/vision-session.md). Без неё
   система честно пишет, что цели нет.
2. Проверить карточки проектов в `empire/state/portfolio.json` — сейчас там записано только
   то, что прозвучало в разговоре 16.09.2026; остальное помечено `null` как вопрос.
3. Подтвердить или переформулировать решения D-001 и D-002 (`python3 tools/empire.py decisions`).

## Ритм

| Когда | Ритуал | Время |
|---|---|---|
| Утро | [`daily-morning.md`](rituals/daily-morning.md) — что сегодня, чего не делаем | 2 мин |
| Вечер | [`daily-close.md`](rituals/daily-close.md) — что закрыто, что выяснилось | 1 мин |
| Понедельник | [`weekly-ceo-review.md`](rituals/weekly-ceo-review.md) — три результата недели | 40 мин |
| По событию | [`new-idea-intake.md`](rituals/new-idea-intake.md) — «а давай ещё сделаем…» | 5 мин |
| По событию | [`board-session.md`](rituals/board-session.md) — крупное решение | 1 час |
| Раз в квартал | [`quarterly-portfolio-review.md`](rituals/quarterly-portfolio-review.md) | 2 часа |

## Структура

```
CONCEPT.md            пять уровней: Vision, Portfolio, CEO OS, Founder Development, Capital
agents/               роли: Chief of Staff, CTO, CPO, CFO/Strategy, Research, Coach, Devil's Advocate
rituals/              что происходит утром, вечером, в понедельник и на совете директоров
templates/            карточка проекта, решение, план недели, протокол совета, проверка навыка
empire/state/         память империи (JSON — правится руками и командами)
empire/STATUS.md      снимок для чтения, генерируется `empire render`
tools/empire.py       ядро: помнит то, что нельзя помнить по памяти
```

## Команды

```bash
python3 tools/empire.py status                      # где мы находимся
python3 tools/empire.py week                        # три результата недели
python3 tools/empire.py stuck                       # чего ты избегаешь
python3 tools/empire.py decision-check "<идея>"     # мы об этом уже договаривались?
python3 tools/empire.py decisions                   # действующие решения
python3 tools/empire.py capacity                    # куда уходят часы
python3 tools/empire.py skills --bottlenecks        # чему сейчас имеет смысл учиться
python3 tools/empire.py portfolio meal-planner      # карточка проекта
python3 tools/empire.py render                      # обновить empire/STATUS.md
```

Полный список: `python3 tools/empire.py --help`. Тесты: `cd tools && python3 -m unittest test_empire`.

## Почему часть системы — код, а не промпт

Всё, что требует суждения, живёт в `agents/` и делается моделью. Всё, что требует **точной
памяти**, живёт в `tools/empire.py`: журнал решений, счётчик дней избегания, правило трёх
результатов, потолок в 100% capacity.

Модель может забыть, что две недели назад вы договорились не расширять scope. `decision-check`
не забудет — и вернёт код 2 ровно в тот момент, когда прозвучит «давай добавим…».
