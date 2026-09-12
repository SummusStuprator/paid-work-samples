"""Small deterministic trivia host; no Roblox or networking dependencies."""
from dataclasses import dataclass
import json
import math


@dataclass(frozen=True)
class Question:
    text: str
    choices: tuple[str, ...]
    answer: int


class Host:
    def __init__(self, players, questions, duration=15):
        players = tuple(players)
        questions = tuple(questions)
        if not players or len(set(players)) != len(players):
            raise ValueError("Players must be nonempty and unique")
        if not questions or not math.isfinite(duration) or duration <= 0:
            raise ValueError("Questions and positive finite duration required")
        if any(not q.choices or type(q.answer) is not int or
               not 0 <= q.answer < len(q.choices) for q in questions):
            raise ValueError("Invalid question")
        self.questions, self.duration = questions, duration
        self.scores = dict.fromkeys(players, 0)
        self.index, self.deadline, self.last_time = -1, None, -math.inf
        self.phase, self.responses = "waiting", {}

    def _time(self, now):
        if not math.isfinite(now) or now < self.last_time:
            raise ValueError("Clock must be finite and monotonic")
        self.last_time = now

    def start(self, now):
        self._time(now)
        if self.phase not in ("waiting", "reveal"):
            raise ValueError("Cannot start while a question is open or game finished")
        if self.index + 1 == len(self.questions):
            self.phase = "finished"
            return self.snapshot()
        self.index += 1
        self.responses = {}
        self.deadline = now + self.duration
        self.phase = "open"
        return self.snapshot()

    def tick(self, now):
        self._time(now)
        if self.phase == "open" and now >= self.deadline:
            self.phase = "reveal"
        return self.snapshot()

    def submit(self, player, question_id, choice, now):
        self.tick(now)
        if self.phase != "open":
            return "closed"
        if player not in self.scores:
            return "unknown-player"
        if type(question_id) is not int or question_id != self.index:
            return "stale-question"
        if player in self.responses:
            return "already-answered"
        q = self.questions[self.index]
        if type(choice) is not int or not 0 <= choice < len(q.choices):
            return "invalid-choice"
        self.responses[player] = choice
        # Do not expose correctness or live scores before reveal.
        if choice == q.answer:
            self.scores[player] += 100
        if len(self.responses) == len(self.scores):
            self.phase = "reveal"
        return "accepted"

    def snapshot(self):
        view = {"phase": self.phase, "question_id": self.index}
        if self.index >= 0:
            q = self.questions[self.index]
            view.update(question=q.text, choices=list(q.choices), deadline=self.deadline,
                        answered=len(self.responses))
            if self.phase in ("reveal", "finished"):
                view.update(answer=q.answer, scores=dict(self.scores))
        return view


def demo():
    host = Host(["Blue", "Gold"], [Question("Which number is prime?", ("21", "29", "39"), 1)])
    print(json.dumps(host.start(0)))
    for args in [("Blue", 0, 1, 2), ("Blue", 0, 0, 3), ("Gold", 0, 2, 15)]:
        print(json.dumps({"submission": args, "result": host.submit(*args)}))
    print(json.dumps(host.snapshot()))
    print(json.dumps(host.start(16)))


if __name__ == "__main__":
    demo()
