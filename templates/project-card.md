# Шаблон карточки проекта

Живёт в `empire/state/portfolio.json`. Здесь — человеческий вид той же карточки.

```text
MEAL PLANNER

Stage: product-development
Potential: ?
Users: ?
Problem: планирование питания и оптимизация готовки
Current milestone: стабилизировать domain model
Next milestone: usable MVP
Monetization: TBD

Стратегические вопросы:
— Для кого продукт?
— Чем лучше Ufff?
— Как получить первых пользователей?
— Что является MVP?
— Что мы сейчас делаем лишнего?
```

## Правило знака вопроса

`?` — это не «забыли заполнить», это «ответа пока нет». Разница принципиальная:

- Пустое поле `user` у проекта в стадии `product-development` — **главный риск проекта**,
  а не косметика карточки.
- Заполнять поля выдуманными ответами запрещено всем ролям. Лучше `?` полгода, чем
  придуманный пользователь, под которого строится продукт.

## Поля

| Поле | Что значит | Кто заполняет |
|---|---|---|
| `stage` | idea → discovery → mvp → product-development → first-users → traction → asset → business | Chief of Staff |
| `problem` | Проблема живого человека, подтверждённая разговором | CPO |
| `problem_hypothesis` | То же, но пока не подтверждённое | CPO |
| `user` | Один конкретный человек, не сегмент | CPO |
| `potential` | Потолок: сколько это может стоить и для скольких людей | CFO |
| `current_milestone` | Что делается прямо сейчас | Chief of Staff |
| `next_milestone` | Следующее проверяемое состояние | CPO + CTO |
| `monetization` | Кто платит и за что | CFO |
| `users_talked_to` / `users_using` | Числа, а не ощущения | Chief of Staff |
| `last_user_contact` | Дата последнего разговора с живым пользователем | Chief of Staff |
| `blockers` | Что физически мешает следующему milestone | все |
| `risk` | Главный способ, которым этот проект провалится | CFO + CPO |

## Стадии, за которыми следят особо

- **`product-development` дольше двух недель при `users_talked_to = 0`** → CPO ставит вопрос
  «стоп development».
- **`idea` с непроведённым discovery** → проект не получает часов сверх `exploration`.
- **`first-users`** → главная метрика меняется: не «что построено», а «что вернулись».
