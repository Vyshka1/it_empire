#!/usr/bin/env python3
"""Тесты ядра. Проверяем механику, из-за которой Empire OS не даёт себя обмануть:
журнал решений, детектор избегания, правило трёх результатов, потолок в 100%."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import empire


class EmpireTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        real = Path(__file__).resolve().parent.parent / "empire" / "state"
        shutil.copytree(real, self.tmp / "state")
        self._orig = empire.STATE
        empire.STATE = self.tmp / "state"

    def tearDown(self):
        empire.STATE = self._orig
        shutil.rmtree(self.tmp)

    def run_cli(self, *argv):
        return empire.main(list(argv))

    def state(self, name):
        return json.loads((empire.STATE / f"{name}.json").read_text("utf-8"))

    def last_commitment(self):
        """Последнее добавленное обязательство: id зависит от живого состояния."""
        return self.state("commitments")["commitments"][-1]

    # --- решения ---

    def test_new_idea_hits_existing_decision(self):
        """Идея, противоречащая действующему решению, не проходит молча."""
        code = self.run_cli("decision-check",
                            "давай добавим новую функцию в Meal Planner")
        self.assertEqual(code, 2)

    def test_unrelated_idea_passes(self):
        code = self.run_cli("decision-check", "купить новый монитор")
        self.assertEqual(code, 0)

    def test_superseded_decision_stops_blocking(self):
        """Сознательная смена решения снимает блок; забывание — нет."""
        before = len(empire.active_decisions(self.state("decisions")))
        self.run_cli("decision-supersede", "D-001",
                     "--what", "Разрешаем новые функции Meal Planner",
                     "--reason", "Унификация расчётов закончена")
        d = self.state("decisions")
        old = next(x for x in d["decisions"] if x["id"] == "D-001")
        self.assertEqual(old["status"], "superseded")
        new = next(x for x in d["decisions"] if x["id"] == old["superseded_by"])
        self.assertEqual(new["supersedes"], "D-001")
        self.assertEqual(new["status"], "active")
        # одно ушло, одно пришло: число действующих решений не меняется
        self.assertEqual(len(empire.active_decisions(d)), before)

    def test_closing_decision_requires_reason(self):
        self.run_cli("decision-close", "D-002", "--reason", "Discovery завершён")
        d = json.loads((empire.STATE / "decisions.json").read_text("utf-8"))
        closed = next(x for x in d["decisions"] if x["id"] == "D-002")
        self.assertEqual(closed["status"], "closed")
        self.assertIn("Discovery", closed["close_reason"])

    # --- обязательства и избегание ---

    def test_untouched_commitment_surfaces_as_avoidance(self):
        before = len(empire.stuck_items())
        self.run_cli("commit-add", "--project", "price-base",
                     "--what", "Написать пяти знакомым про базу цен")
        c = self.state("commitments")
        c["commitments"][-1]["created"] = "2026-09-10"
        (empire.STATE / "commitments.json").write_text(
            json.dumps(c, ensure_ascii=False), encoding="utf-8")
        stuck = empire.stuck_items()
        self.assertEqual(len(stuck), before + 1)
        self.assertGreaterEqual(stuck[0][1], empire.AVOIDANCE_DAYS)

    def test_touch_clears_avoidance(self):
        self.run_cli("commit-add", "--project", "meal-planner",
                     "--what", "Дать продукт первому человеку")
        cid = self.last_commitment()["id"]
        self.run_cli("commit-touch", cid)
        self.assertNotIn(cid, [x["id"] for x, _ in empire.stuck_items()])

    def test_dropped_commitment_keeps_its_reason(self):
        self.run_cli("commit-add", "--project", "signal-system", "--what", "X")
        cid = self.last_commitment()["id"]
        self.run_cli("commit-drop", cid, "--reason", "Заморожено D-002")
        dropped = self.last_commitment()
        self.assertEqual(dropped["status"], "dropped")
        self.assertEqual(dropped["drop_reason"], "Заморожено D-002")
        self.assertNotIn(cid, [x["id"] for x in
                               empire.open_commitments(self.state("commitments"))])

    # --- неделя ---

    def test_week_plan_demands_exactly_three_outcomes(self):
        for n in (2, 4):
            args = ["week-plan", "--week", "2026-W99"]
            for i in range(n):
                args += ["--result", f"meal-planner:результат {i}"]
            self.assertEqual(self.run_cli(*args), 1)

    def test_week_plan_accepts_three(self):
        code = self.run_cli(
            "week-plan", "--week", "2026-W99",
            "--result", "meal-planner:A", "--result", "price-base:B",
            "--result", "founder:C", "--not-doing", "Signal")
        self.assertEqual(code, 0)
        w = json.loads((empire.STATE / "weeks.json").read_text("utf-8"))
        added = next(x for x in w["weeks"] if x["week"] == "2026-W99")
        self.assertEqual([o["n"] for o in added["outcomes"]], [1, 2, 3])
        self.assertEqual(added["not_doing"], ["Signal"])

    def test_week_done_marks_outcome(self):
        self.run_cli("week-done", "1", "--week", "2026-W38")
        w = json.loads((empire.STATE / "weeks.json").read_text("utf-8"))
        week = next(x for x in w["weeks"] if x["week"] == "2026-W38")
        self.assertTrue(week["outcomes"][0]["done"])

    # --- capacity и навыки ---

    def test_capacity_over_hundred_is_rejected_visibly(self):
        self.run_cli("capacity-set", "meal-planner=60", "price-base=60",
                     "--week", "2026-W38")
        cap = json.loads((empire.STATE / "capacity.json").read_text("utf-8"))
        a = empire.get_alloc(cap, "2026-W38")
        self.assertEqual(sum(a["planned"].values()), 120)  # видно в выводе

    def test_bottleneck_limit(self):
        sk = json.loads((empire.STATE / "skills.json").read_text("utf-8"))
        self.assertLessEqual(len(empire.bottlenecks(sk)), 2,
                             "Больше двух bottleneck — учимся вместо стройки")

    def test_skill_set_records_assessment(self):
        self.run_cli("skill-set", "PRODUCT/prioritization", "--level", "2",
                     "--bottleneck", "yes", "--evidence", "кейс провален")
        sk = json.loads((empire.STATE / "skills.json").read_text("utf-8"))
        s = sk["areas"]["PRODUCT"]["prioritization"]
        self.assertEqual(s["level"], 2)
        self.assertTrue(s["bottleneck"])
        self.assertEqual(len(sk["assessments"]), 1)

    # --- идеи ---

    def test_idea_goes_to_backlog_not_portfolio(self):
        self.run_cli("idea-add", "Приложение для трекинга воды")
        ideas = json.loads((empire.STATE / "ideas.json").read_text("utf-8"))
        pf = json.loads((empire.STATE / "portfolio.json").read_text("utf-8"))
        self.assertEqual(ideas["ideas"][0]["verdict"], "backlog")
        self.assertEqual(len(pf["projects"]), 3)

    # --- личные проекты ---

    def test_personal_project_is_out_of_commercial_portfolio(self):
        """С личного инструмента империя не требует пользователей и денег."""
        pf = json.loads((empire.STATE / "portfolio.json").read_text("utf-8"))
        personal = [p for p in pf["projects"] if p["stage"] == "personal"]
        self.assertTrue(personal, "Meal Planner должен быть личным (D-008)")
        ids = {p["id"] for p in empire.commercial_projects(pf)}
        for p in personal:
            self.assertNotIn(p["id"], ids)

    def test_personal_project_has_no_monetization_demand(self):
        pf = json.loads((empire.STATE / "portfolio.json").read_text("utf-8"))
        for p in pf["projects"]:
            if p["stage"] == "personal":
                self.assertIsNotNone(p["monetization"])
                self.assertNotIn("TBD", p["monetization"])

    # --- целостность состояния ---

    def test_portfolio_stages_are_valid(self):
        pf = json.loads((empire.STATE / "portfolio.json").read_text("utf-8"))
        for p in pf["projects"]:
            self.assertIn(p["stage"], pf["stages"])

    def test_week_outcomes_reference_known_projects(self):
        pf = json.loads((empire.STATE / "portfolio.json").read_text("utf-8"))
        w = json.loads((empire.STATE / "weeks.json").read_text("utf-8"))
        known = {p["id"] for p in pf["projects"]} | {"founder", "empire"}
        for week in w["weeks"]:
            for o in week["outcomes"]:
                self.assertIn(o["project"], known)

    def test_blocked_project_names_a_live_decision(self):
        """Заморозка проекта должна ссылаться на решение, которое ещё живо."""
        pf = json.loads((empire.STATE / "portfolio.json").read_text("utf-8"))
        d = json.loads((empire.STATE / "decisions.json").read_text("utf-8"))
        live = {x["id"] for x in empire.active_decisions(d)}
        for p in pf["projects"]:
            for b in p.get("blockers", []):
                for ref in __import__("re").findall(r"D-\d{3}", b):
                    self.assertIn(ref, live)


if __name__ == "__main__":
    unittest.main(verbosity=2)
