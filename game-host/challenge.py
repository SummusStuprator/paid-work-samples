"""Short, reproducible recording demo. All players and timestamps are synthetic."""
from host import Host, Question


def main():
    host = Host(["Blue", "Gold"], [Question("Which is prime?", ("21", "29", "39"), 1)] * 2)
    print("CAN YOU FOOL AN AI-WRITTEN QUIZ REFEREE?")
    print("Deterministic local Python. No AI calls. No network.")
    host.start(0)
    print("\nOne ordinary answer:", host.submit("Blue", 0, 1, 2))
    print("Attempt 1 - answer again:", host.submit("Blue", 0, 1, 3))
    print("Answer exposed before reveal:", "answer" in host.snapshot())
    print("Scores exposed before reveal:", "scores" in host.snapshot())
    print("Attempt 2 - answer at the exact deadline:", host.submit("Gold", 0, 1, 15))
    print("Revealed scores:", host.snapshot()["scores"])
    host.start(16)
    print("Attempt 3 - replay the previous question:", host.submit("Gold", 0, 1, 17))
    print("Answers accepted for the new question:", host.snapshot()["answered"])
    print("\nThese cases pass. What case did the author miss?")
    print("Run: python -m unittest -v")


if __name__ == "__main__":
    main()
