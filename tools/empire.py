#!/usr/bin/env python3
"""Empire OS — операционное ядро.

Хранит состояние империи в empire/state/*.json и отвечает на вопросы,
на которые нельзя отвечать по памяти: что обещано, что решено, чего
избегаем, куда уходят часы.

Роли (agents/) думают. Этот файл — помнит.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "empire" / "state"

AVOIDANCE_DAYS = 3
CAPACITY_DRIFT_PP = 15


# --- состояние ---------------------------------------------------------------

def load(name: str) -> dict:
    return json.loads((STATE / f"{name}.json").read_text(encoding="utf-8"))


def save(name: str, data: dict) -> None:
    path = STATE / f"{name}.json"
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def today() -> str:
    return dt.date.today().isoformat()


def current_week() -> str:
    y, w, _ = dt.date.today().isocalendar()
    return f"{y}-W{w:02d}"


def days_since(iso: str | None) -> int | None:
    if not iso:
        return None
    return (dt.date.today() - dt.date.fromisoformat(iso)).days


# --- сопоставление текста (грубое, для русского языка) -----------------------

STOP = {
    "этот", "тот", "того", "чтобы", "нужно", "надо", "может", "быть", "если",
    "когда", "будет", "давай", "можно", "очень", "сейчас", "ещё", "еще",
    "новый", "новая", "новое", "новые", "который", "которая", "какой",
}


def stems(text: str) -> set[str]:
    """Слова длиной от 4 символов, обрезанные до 5 — вместо морфологии."""
    words = re.findall(r"[\w-]+", (text or "").lower())
    return {w[:5] for w in words if len(w) >= 4 and w not in STOP}


def overlap(a: str, b: str) -> int:
    return len(stems(a) & stems(b))


# --- вывод -------------------------------------------------------------------

def head(title: str) -> None:
    print(f"\n{title}")
    print("─" * max(len(title), 12))


def bar(pct: float, width: int = 20) -> str:
    filled = int(round(pct / 100 * width))
    return "█" * filled + "·" * (width - filled)


# --- портфель ----------------------------------------------------------------

def find_project(portfolio: dict, pid: str) -> dict | None:
    for p in portfolio["projects"]:
        if p["id"] == pid:
            return p
    return None


def cmd_portfolio(args) -> int:
    pf = load("portfolio")
    if args.project:
        p = find_project(pf, args.project)
        if not p:
            print(f"Нет проекта '{args.project}'", file=sys.stderr)
            return 1
        print_project_card(p)
        return 0
    head("ПОРТФЕЛЬ")
    for p in pf["projects"]:
        contact = days_since(p.get("last_user_contact"))
        contact_s = (
            "пользователей не видел никогда"
            if contact is None
            else f"последний контакт с пользователем {contact} дн. назад"
        )
        print(f"  {p['name']:<28} {p['stage']:<22} {contact_s}")
        if p.get("blockers"):
            for b in p["blockers"]:
                print(f"      ⚠ {b}")
    return 0


def print_project_card(p: dict) -> None:
    head(p["name"].upper())
    unknown = "?"
    rows = [
        ("Stage", p["stage"]),
        ("Problem", p.get("problem") or p.get("problem_hypothesis") or unknown),
        ("User", p.get("user") or unknown),
        ("Potential", p.get("potential") or unknown),
        ("Current milestone", p.get("current_milestone") or unknown),
        ("Next milestone", p.get("next_milestone") or unknown),
        ("Monetization", p.get("monetization") or unknown),
        ("Говорили с пользователями", p.get("users_talked_to", 0)),
        ("Пользуются", p.get("users_using", 0)),
    ]
    for k, v in rows:
        print(f"  {k:<26} {v}")
    if p.get("blockers"):
        print("\n  Блокеры:")
        for b in p["blockers"]:
            print(f"    — {b}")
    if p.get("risk"):
        print(f"\n  Риск: {p['risk']}")
    if p.get("strategic_questions"):
        print("\n  Стратегические вопросы:")
        for q in p["strategic_questions"]:
            print(f"    — {q}")


# --- неделя ------------------------------------------------------------------

def get_week(weeks: dict, week: str) -> dict | None:
    for w in weeks["weeks"]:
        if w["week"] == week:
            return w
    return None


def cmd_week(args) -> int:
    weeks = load("weeks")
    week = args.week or current_week()
    w = get_week(weeks, week)
    if not w:
        print(f"План на {week} не составлен. Это делается на CEO Review "
              f"(rituals/weekly-ceo-review.md).")
        return 1
    head(f"НЕДЕЛЯ {week}")
    for o in w["outcomes"]:
        mark = "✔" if o["done"] else "·"
        print(f"  {mark} #{o['n']} [{o['project']}] {o['result']}")
    if w.get("not_doing"):
        print("\n  НЕ ДЕЛАТЬ:")
        for nd in w["not_doing"]:
            print(f"    — {nd}")
    return 0


def cmd_week_done(args) -> int:
    weeks = load("weeks")
    w = get_week(weeks, args.week or current_week())
    if not w:
        print("Нет плана на эту неделю", file=sys.stderr)
        return 1
    for o in w["outcomes"]:
        if o["n"] == args.n:
            o["done"] = True
            save("weeks", weeks)
            print(f"Результат #{args.n} закрыт: {o['result']}")
            return 0
    print(f"Нет результата #{args.n}", file=sys.stderr)
    return 1


def cmd_week_plan(args) -> int:
    weeks = load("weeks")
    week = args.week or current_week()
    if get_week(weeks, week):
        print(f"План на {week} уже есть — правь его, а не создавай второй.",
              file=sys.stderr)
        return 1
    results = args.result or []
    if len(results) != 3:
        print("Ровно три результата. Не два и не пять — три.", file=sys.stderr)
        return 1
    outcomes = []
    for i, r in enumerate(results, start=1):
        project, _, text = r.partition(":")
        if not text:
            print(f"Формат результата: 'project:что именно' (получено: {r})",
                  file=sys.stderr)
            return 1
        outcomes.append({"n": i, "project": project.strip(),
                         "result": text.strip(), "done": False})
    weeks["weeks"].append({
        "week": week,
        "outcomes": outcomes,
        "not_doing": args.not_doing or [],
        "review": None,
    })
    save("weeks", weeks)
    print(f"План на {week} записан.")
    return cmd_week(argparse.Namespace(week=week))


# --- обязательства -----------------------------------------------------------

def cmd_commit_add(args) -> int:
    c = load("commitments")
    cid = f"C-{c['next_id']:03d}"
    c["next_id"] += 1
    c["commitments"].append({
        "id": cid,
        "project": args.project,
        "what": args.what,
        "due": args.due,
        "status": "open",
        "created": today(),
        "touched": [],
        "week": current_week(),
    })
    save("commitments", c)
    print(f"{cid} записано. Теперь это обещание, а не идея.")
    return 0


def open_commitments(c: dict) -> list[dict]:
    return [x for x in c["commitments"] if x["status"] == "open"]


def cmd_commit_list(args) -> int:
    c = load("commitments")
    items = c["commitments"] if args.all else open_commitments(c)
    if not items:
        print("Открытых обязательств нет.")
        return 0
    head("ОБЯЗАТЕЛЬСТВА")
    for x in items:
        idle = days_since(x["touched"][-1] if x["touched"] else x["created"])
        due = f"до {x['due']}" if x.get("due") else "без срока"
        flag = "  ← избегание" if x["status"] == "open" and idle is not None \
            and idle >= AVOIDANCE_DAYS else ""
        print(f"  {x['id']} [{x['project']}] {x['what']}")
        print(f"       {x['status']}, {due}, не трогали {idle} дн.{flag}")
    return 0


def _find_commit(c: dict, cid: str) -> dict | None:
    for x in c["commitments"]:
        if x["id"] == cid.upper():
            return x
    return None


def cmd_commit_touch(args) -> int:
    c = load("commitments")
    x = _find_commit(c, args.id)
    if not x:
        print(f"Нет обязательства {args.id}", file=sys.stderr)
        return 1
    if today() not in x["touched"]:
        x["touched"].append(today())
    save("commitments", c)
    print(f"{x['id']}: работа сегодня зафиксирована.")
    return 0


def cmd_commit_done(args) -> int:
    c = load("commitments")
    x = _find_commit(c, args.id)
    if not x:
        print(f"Нет обязательства {args.id}", file=sys.stderr)
        return 1
    x["status"] = "done"
    x["closed"] = today()
    if today() not in x["touched"]:
        x["touched"].append(today())
    save("commitments", c)
    print(f"{x['id']} закрыто.")
    return 0


def cmd_commit_drop(args) -> int:
    c = load("commitments")
    x = _find_commit(c, args.id)
    if not x:
        print(f"Нет обязательства {args.id}", file=sys.stderr)
        return 1
    x["status"] = "dropped"
    x["closed"] = today()
    x["drop_reason"] = args.reason
    save("commitments", c)
    print(f"{x['id']} снято. Причина записана — снятое обязательство "
          f"тоже факт о тебе.")
    return 0


def stuck_items(days: int = AVOIDANCE_DAYS) -> list[tuple[dict, int]]:
    c = load("commitments")
    out = []
    for x in open_commitments(c):
        idle = days_since(x["touched"][-1] if x["touched"] else x["created"])
        if idle is not None and idle >= days:
            out.append((x, idle))
    return sorted(out, key=lambda t: -t[1])


def cmd_stuck(args) -> int:
    items = stuck_items(args.days)
    if not items:
        print("Обязательств, которых ты избегаешь, нет.")
        return 0
    head("ИЗБЕГАНИЕ")
    print("Это не список задач. Это вопрос «почему именно эта задача стоит».\n")
    for x, idle in items:
        print(f"  {x['id']} [{x['project']}] {x['what']}")
        print(f"       открыто {days_since(x['created'])} дн., "
              f"без движения {idle} дн.")
    print("\n  Разбор: rituals/daily-morning.md → раздел «Избегание».")
    return 0


# --- решения -----------------------------------------------------------------

def active_decisions(d: dict) -> list[dict]:
    return [x for x in d["decisions"] if x["status"] == "active"]


def cmd_decision_list(args) -> int:
    d = load("decisions")
    items = d["decisions"] if args.all else active_decisions(d)
    head("РЕШЕНИЯ" + ("" if args.all else " (действующие)"))
    for x in items:
        print(f"  {x['id']} · {x['date']} · {x['project'] or 'империя'} "
              f"· {x['status']}")
        print(f"       {x['decision']}")
        print(f"       Причина: {x['reason']}")
        if x.get("revisit_after"):
            print(f"       Вернуться когда: {x['revisit_after']}")
    return 0


def cmd_decision_add(args) -> int:
    d = load("decisions")
    n = len(d["decisions"]) + 1
    did = f"D-{n:03d}"
    d["decisions"].append({
        "id": did,
        "date": today(),
        "project": args.project,
        "decision": args.what,
        "reason": args.reason,
        "revisit_after": args.revisit,
        "tags": [t.strip() for t in (args.tags or "").split(",") if t.strip()],
        "status": "active",
        "superseded_by": None,
        "source": args.source or "CEO Review",
    })
    save("decisions", d)
    print(f"{did} записано. Через две недели ты не вспомнишь причину — "
          f"а лог вспомнит.")
    return 0


def cmd_decision_close(args) -> int:
    d = load("decisions")
    for x in d["decisions"]:
        if x["id"] == args.id.upper():
            x["status"] = "closed"
            x["closed"] = today()
            x["close_reason"] = args.reason
            save("decisions", d)
            print(f"{x['id']} закрыто: условие возврата выполнено.")
            return 0
    print(f"Нет решения {args.id}", file=sys.stderr)
    return 1


def cmd_decision_supersede(args) -> int:
    d = load("decisions")
    old = next((x for x in d["decisions"] if x["id"] == args.id.upper()), None)
    if not old:
        print(f"Нет решения {args.id}", file=sys.stderr)
        return 1
    n = len(d["decisions"]) + 1
    new_id = f"D-{n:03d}"
    d["decisions"].append({
        "id": new_id,
        "date": today(),
        "project": old["project"],
        "decision": args.what,
        "reason": args.reason,
        "revisit_after": args.revisit,
        "tags": old.get("tags", []),
        "status": "active",
        "superseded_by": None,
        "supersedes": old["id"],
        "source": "Сознательная смена решения",
    })
    old["status"] = "superseded"
    old["superseded_by"] = new_id
    save("decisions", d)
    print(f"{old['id']} → {new_id}. Решение изменено сознательно, "
          f"а не забыто — это разные вещи.")
    return 0


def check_text(text: str) -> list[tuple[dict, int]]:
    d = load("decisions")
    hits = []
    for x in active_decisions(d):
        haystack = " ".join(filter(None, [
            x["decision"], x["reason"], x.get("project") or "",
            " ".join(x.get("tags", [])),
        ]))
        score = overlap(text, haystack)
        if x.get("project") and x["project"] in text.lower():
            score += 3
        if score >= 2:
            hits.append((x, score))
    return sorted(hits, key=lambda t: -t[1])


def cmd_decision_check(args) -> int:
    text = " ".join(args.text)
    hits = check_text(text)
    if not hits:
        print("Действующих решений по этой теме нет — вопрос открыт.")
        return 0
    head("МЫ ОБ ЭТОМ УЖЕ ДОГОВАРИВАЛИСЬ")
    for x, _ in hits:
        print(f"  {x['id']} ({x['date']}): {x['decision']}")
        print(f"       Причина: {x['reason']}")
        if x.get("revisit_after"):
            print(f"       Условие возврата: {x['revisit_after']}")
        print()
    print("  Условие возврата уже выполнено — или мы сознательно меняем "
          "решение?")
    print("  Меняем: empire decision supersede <ID> --what ... --reason ...")
    return 2


# --- capacity ----------------------------------------------------------------

def get_alloc(cap: dict, week: str) -> dict | None:
    for a in cap["allocations"]:
        if a["week"] == week:
            return a
    return None


def cmd_capacity(args) -> int:
    cap = load("capacity")
    week = args.week or current_week()
    a = get_alloc(cap, week)
    if not a:
        print(f"Распределение на {week} не задано.")
        return 1
    head(f"CAPACITY {week}")
    hours = cap.get("hours_per_week")
    print(f"  100% ёмкости основателя"
          f"{f' ≈ {hours} ч/нед' if hours else ' (часы в неделю не заданы — задай их)'}\n")
    keys = list(a["planned"]) + [k for k in a.get("actual", {})
                                 if k not in a["planned"]]
    for k in keys:
        p = a["planned"].get(k, 0)
        act = a.get("actual", {}).get(k)
        line = f"  {bar(p)}  {k:<18} план {p:>3}%"
        if act is not None:
            drift = act - p
            line += f"   факт {act:>3}%"
            if abs(drift) >= CAPACITY_DRIFT_PP:
                line += f"   ⚠ расхождение {drift:+d} п.п."
        print(line)
    total = sum(a["planned"].values())
    if total != 100:
        print(f"\n  ⚠ План даёт {total}%. Часов не станет больше — "
              f"что-то нужно сократить.")
    if a.get("actual"):
        drifted = [k for k in a["planned"]
                   if abs(a["actual"].get(k, 0) - a["planned"][k])
                   >= CAPACITY_DRIFT_PP]
        if drifted:
            print(f"\n  Разобрать на CEO Review: {', '.join(drifted)}")
    return 0


def _parse_pairs(pairs: list[str]) -> dict:
    out = {}
    for p in pairs:
        k, _, v = p.partition("=")
        out[k.strip()] = int(v)
    return out


def cmd_capacity_set(args) -> int:
    cap = load("capacity")
    week = args.week or current_week()
    a = get_alloc(cap, week)
    if not a:
        a = {"week": week, "planned": {}, "actual": {}}
        cap["allocations"].append(a)
    field = "actual" if args.actual else "planned"
    a[field] = _parse_pairs(args.pairs)
    cap["current_week"] = week
    save("capacity", cap)
    return cmd_capacity(argparse.Namespace(week=week))


# --- навыки ------------------------------------------------------------------

def bottlenecks(sk: dict) -> list[tuple[str, str, dict]]:
    return [(area, name, s)
            for area, skills in sk["areas"].items()
            for name, s in skills.items() if s.get("bottleneck")]


def cmd_skills(args) -> int:
    sk = load("skills")
    if args.bottlenecks:
        bs = bottlenecks(sk)
        head("BOTTLENECKS")
        if not bs:
            print("  Активных bottleneck нет — учиться сейчас не нужно, "
                  "нужно строить.")
            return 0
        for area, name, s in bs:
            print(f"  {area}/{name}   уровень: {s['level'] if s['level'] is not None else 'не оценён'}")
            if s.get("evidence"):
                print(f"       Почему: {s['evidence']}")
        if len(bs) > 2:
            print(f"\n  ⚠ {len(bs)} bottleneck одновременно. "
                  f"Правило: не больше двух.")
        return 0
    head("FOUNDER SKILL MAP")
    for area, skills in sk["areas"].items():
        print(f"\n  {area}")
        for name, s in skills.items():
            lvl = s["level"] if s["level"] is not None else "—"
            mark = " ← bottleneck" if s.get("bottleneck") else ""
            print(f"    {name:<22} {lvl}{mark}")
    print("\n  Пустая клетка — не пробел. Учим только bottleneck.")
    return 0


def cmd_skill_set(args) -> int:
    sk = load("skills")
    area, _, name = args.skill.partition("/")
    if area not in sk["areas"] or name not in sk["areas"][area]:
        print(f"Нет навыка {args.skill}. Формат: AREA/skill-name",
              file=sys.stderr)
        return 1
    s = sk["areas"][area][name]
    if args.level is not None:
        s["level"] = args.level
    if args.bottleneck is not None:
        s["bottleneck"] = args.bottleneck == "yes"
    if args.evidence:
        s["evidence"] = args.evidence
    sk["assessments"].append({
        "date": today(), "skill": args.skill,
        "level": s["level"], "bottleneck": s["bottleneck"],
    })
    save("skills", sk)
    print(f"{args.skill}: уровень {s['level']}, "
          f"bottleneck {'да' if s['bottleneck'] else 'нет'}")
    bs = bottlenecks(sk)
    if len(bs) > 2:
        print(f"⚠ Теперь {len(bs)} bottleneck. Империя строится, "
              f"пока ты учишься максимум двум вещам.")
    return 0


# --- идеи --------------------------------------------------------------------

def cmd_idea_add(args) -> int:
    ideas = load("ideas")
    iid = f"I-{ideas['next_id']:03d}"
    ideas["next_id"] += 1
    ideas["ideas"].append({
        "id": iid, "date": today(), "what": args.what,
        "relation": None, "cost": None, "verdict": "backlog",
    })
    save("ideas", ideas)
    print(f"{iid} в бэклоге. Ноль часов до intake "
          f"(rituals/new-idea-intake.md).")
    hits = check_text(args.what)
    if hits:
        print()
        cmd_decision_check(argparse.Namespace(text=[args.what]))
    return 0


def cmd_idea_list(args) -> int:
    ideas = load("ideas")
    if not ideas["ideas"]:
        print("Бэклог идей пуст.")
        return 0
    head("ИДЕИ")
    for i in ideas["ideas"]:
        print(f"  {i['id']} · {i['date']} · {i['verdict']}")
        print(f"       {i['what']}")
    return 0


# --- уроки -------------------------------------------------------------------

def cmd_lesson_add(args) -> int:
    ls = load("lessons")
    lid = f"L-{ls['next_id']:03d}"
    ls["next_id"] += 1
    ls["lessons"].append({
        "id": lid, "date": today(), "project": args.project,
        "lesson": args.what, "cost": args.cost,
    })
    save("lessons", ls)
    print(f"{lid} записан.")
    return 0


def cmd_lesson_list(args) -> int:
    ls = load("lessons")
    if not ls["lessons"]:
        print("Уроков пока нет.")
        return 0
    head("УРОКИ")
    for l in ls["lessons"]:
        print(f"  {l['id']} · {l['date']} · {l['project'] or 'империя'}")
        print(f"       {l['lesson']}")
        if l.get("cost"):
            print(f"       Стоило: {l['cost']}")
    return 0


# --- статус ------------------------------------------------------------------

def cmd_status(args) -> int:
    week = current_week()
    vision = load("vision")
    pf = load("portfolio")
    c = load("commitments")
    d = load("decisions")
    sk = load("skills")

    head(f"EMPIRE OS · {today()} · {week}")

    if vision["horizons"]["1y"]["target"] is None:
        print("  ⚠ Vision не заполнен. Портфель без цели — это набор "
              "пет-проектов.\n    Первая сессия: rituals/vision-session.md")

    cmd_week(argparse.Namespace(week=week))
    cmd_portfolio(argparse.Namespace(project=None))

    live = [p for p in pf["projects"] if p.get("users_using", 0) > 0]
    if not live:
        print("\n  ⚠ Ни одним продуктом портфеля никто не пользуется. "
              "Активов пока ноль.")

    op = open_commitments(c)
    head(f"ОБЯЗАТЕЛЬСТВА: {len(op)} открыто")
    for x in op:
        idle = days_since(x["touched"][-1] if x["touched"] else x["created"])
        print(f"  {x['id']} [{x['project']}] {x['what']} "
              f"— без движения {idle} дн.")

    st = stuck_items()
    if st:
        print(f"\n  ⚠ Избегание: {len(st)} обязательств стоят "
              f"{AVOIDANCE_DAYS}+ дн. → empire stuck")

    bs = bottlenecks(sk)
    head("BOTTLENECKS")
    for area, name, s in bs:
        print(f"  {area}/{name} — {s.get('evidence') or 'причина не записана'}")

    print(f"\nДействующих решений: {len(active_decisions(d))} "
          f"→ empire decisions")
    return 0


def cmd_render(args) -> int:
    """Собирает empire/STATUS.md — снимок для чтения глазами и для контекста."""
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_status(argparse.Namespace())
        cmd_decision_list(argparse.Namespace(all=False))
    body = buf.getvalue()
    out = ROOT / "empire" / "STATUS.md"
    out.write_text(
        f"# Статус империи\n\n"
        f"<!-- Файл генерируется: python3 tools/empire.py render. "
        f"Правь состояние в empire/state/, а не здесь. -->\n\n"
        f"```\n{body.strip()}\n```\n",
        encoding="utf-8",
    )
    print(f"Записано: {out.relative_to(ROOT)}")
    return 0


# --- разбор аргументов -------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="empire", description="Empire OS — операционное ядро")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="общий снимок империи").set_defaults(
        func=cmd_status)
    sub.add_parser("render", help="записать empire/STATUS.md").set_defaults(
        func=cmd_render)

    pp = sub.add_parser("portfolio", help="портфель или карточка проекта")
    pp.add_argument("project", nargs="?")
    pp.set_defaults(func=cmd_portfolio)

    w = sub.add_parser("week", help="план недели")
    w.add_argument("--week")
    w.set_defaults(func=cmd_week)

    wp = sub.add_parser("week-plan", help="составить план недели (3 результата)")
    wp.add_argument("--week")
    wp.add_argument("--result", action="append",
                    help="'project:что именно' (ровно три раза)")
    wp.add_argument("--not-doing", action="append", dest="not_doing")
    wp.set_defaults(func=cmd_week_plan)

    wd = sub.add_parser("week-done", help="закрыть результат недели")
    wd.add_argument("n", type=int)
    wd.add_argument("--week")
    wd.set_defaults(func=cmd_week_done)

    ca = sub.add_parser("commit-add", help="записать обязательство")
    ca.add_argument("--project", required=True)
    ca.add_argument("--what", required=True)
    ca.add_argument("--due")
    ca.set_defaults(func=cmd_commit_add)

    cl = sub.add_parser("commitments", help="список обязательств")
    cl.add_argument("--all", action="store_true")
    cl.set_defaults(func=cmd_commit_list)

    for name, fn, extra in (
        ("commit-touch", cmd_commit_touch, None),
        ("commit-done", cmd_commit_done, None),
        ("commit-drop", cmd_commit_drop, "reason"),
    ):
        sp = sub.add_parser(name)
        sp.add_argument("id")
        if extra:
            sp.add_argument("--reason", required=True)
        sp.set_defaults(func=fn)

    st = sub.add_parser("stuck", help="чего ты избегаешь")
    st.add_argument("--days", type=int, default=AVOIDANCE_DAYS)
    st.set_defaults(func=cmd_stuck)

    dl = sub.add_parser("decisions", help="журнал решений")
    dl.add_argument("--all", action="store_true")
    dl.set_defaults(func=cmd_decision_list)

    da = sub.add_parser("decision-add")
    da.add_argument("--project")
    da.add_argument("--what", required=True)
    da.add_argument("--reason", required=True)
    da.add_argument("--revisit")
    da.add_argument("--tags")
    da.add_argument("--source")
    da.set_defaults(func=cmd_decision_add)

    dch = sub.add_parser(
        "decision-check",
        help="проверить идею против действующих решений (код 2 — есть совпадения)")
    dch.add_argument("text", nargs="+")
    dch.set_defaults(func=cmd_decision_check)

    dc = sub.add_parser("decision-close")
    dc.add_argument("id")
    dc.add_argument("--reason", required=True)
    dc.set_defaults(func=cmd_decision_close)

    ds = sub.add_parser("decision-supersede")
    ds.add_argument("id")
    ds.add_argument("--what", required=True)
    ds.add_argument("--reason", required=True)
    ds.add_argument("--revisit")
    ds.set_defaults(func=cmd_decision_supersede)

    cp = sub.add_parser("capacity", help="распределение часов")
    cp.add_argument("--week")
    cp.set_defaults(func=cmd_capacity)

    cs = sub.add_parser("capacity-set", help="задать план или факт")
    cs.add_argument("pairs", nargs="+", help="project=процент")
    cs.add_argument("--actual", action="store_true")
    cs.add_argument("--week")
    cs.set_defaults(func=cmd_capacity_set)

    sm = sub.add_parser("skills", help="карта навыков")
    sm.add_argument("--bottlenecks", action="store_true")
    sm.set_defaults(func=cmd_skills)

    ss = sub.add_parser("skill-set")
    ss.add_argument("skill", help="AREA/skill-name")
    ss.add_argument("--level", type=int, choices=range(0, 6))
    ss.add_argument("--bottleneck", choices=["yes", "no"])
    ss.add_argument("--evidence")
    ss.set_defaults(func=cmd_skill_set)

    ia = sub.add_parser("idea-add", help="положить идею в бэклог")
    ia.add_argument("what")
    ia.set_defaults(func=cmd_idea_add)

    sub.add_parser("ideas").set_defaults(func=cmd_idea_list)

    la = sub.add_parser("lesson-add")
    la.add_argument("what")
    la.add_argument("--project")
    la.add_argument("--cost")
    la.set_defaults(func=cmd_lesson_add)

    sub.add_parser("lessons").set_defaults(func=cmd_lesson_list)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
