import unittest
from host import Host, Question


class HostTests(unittest.TestCase):
    def setUp(self):
        self.h = Host(["A", "B"], [Question("Q", ("no", "yes"), 1)] * 2)
        self.h.start(0)

    def test_duplicate_cannot_score_twice(self):
        self.assertEqual(self.h.submit("A", 0, 1, 1), "accepted")
        self.assertEqual(self.h.submit("A", 0, 1, 2), "already-answered")
        self.assertEqual(self.h.scores["A"], 100)

    def test_exact_deadline_is_closed(self):
        self.assertEqual(self.h.submit("A", 0, 1, 15), "closed")
        self.assertEqual(self.h.scores["A"], 0)
        self.assertEqual(self.h.phase, "reveal")

    def test_delayed_packet_does_not_answer_next_question(self):
        self.h.tick(15)
        self.h.start(16)
        self.assertEqual(self.h.submit("A", 0, 1, 17), "stale-question")
        self.assertEqual(self.h.responses, {})

    def test_no_answer_or_score_leak_before_reveal(self):
        self.h.submit("A", 0, 1, 1)
        self.assertNotIn("answer", self.h.snapshot())
        self.assertNotIn("scores", self.h.snapshot())
        self.h.submit("B", 0, 0, 2)
        self.assertEqual(self.h.snapshot()["scores"], {"A": 100, "B": 0})

    def test_invalid_input_does_not_consume_turn(self):
        for choice in (-1, 2, True, 1.0):
            self.assertEqual(self.h.submit("A", 0, choice, 1), "invalid-choice")
        self.assertEqual(self.h.submit("stranger", 0, 1, 1), "unknown-player")
        self.assertEqual(self.h.submit("A", 0, 1, 1), "accepted")

    def test_clock_and_state_errors(self):
        with self.assertRaises(ValueError):
            self.h.start(1)
        for now in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.h.tick(now)

    def test_game_finishes_without_extra_question(self):
        self.h.tick(15)
        self.h.start(16)
        self.h.tick(31)
        self.assertEqual(self.h.start(32)["phase"], "finished")
        with self.assertRaises(ValueError):
            self.h.start(33)


if __name__ == "__main__":
    unittest.main()
