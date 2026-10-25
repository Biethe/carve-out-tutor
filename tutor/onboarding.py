"""First-launch onboarding: three yes/no questions from a fixed tree, every line pre-recorded in Chip's voice.
No AI and no key needed, so it's instant and sounds the same for everyone. (Improve my profile, later, uses the AI.)
Q1 is about Python; Q2 about the web, harder after a yes and easier after a no; Q3 about data, the same way."""

# id: (what Chip says, the skill a yes shows)
QUESTIONS = {
    "python": ("Have you written your own Python functions before?", "Writing Python functions"),
    "web_hard": ("Have you built a web app with a login form?", "Web apps with a login"),
    "web_easy": ("Have you made a web page before?", "Making web pages"),
    "data_hard": ("Have you stored passwords safely, with hashing?", "Password hashing"),
    "data_easy": ("Have you saved data in a database before?", "Saving data in a database"),
}
# Everything Chip says during onboarding, recorded once (tutor/record_intro.py): clip id -> words.
LINES = {
    "intro": "Hey, I'm Chip. You'll rebuild small pieces of a real app... and it keeps running, on your code. "
             "Three quick yes or no questions, and we're off.",
    **{qid: text for qid, (text, _) in QUESTIONS.items()},
    "yes": "Nice.",
    "no": "No problem.",
    "again": "Sorry, was that a yes, or a no?",
    "closing": "That's all I need. Let's build.",
}


def tree() -> dict:
    """What the page needs: the first question, and which question follows a yes or a no."""
    return {"first": "python", "next": {"python": ["web_hard", "web_easy"], "web_hard": ["data_hard", "data_easy"],
                                        "web_easy": ["data_hard", "data_easy"]},
            "questions": {qid: text for qid, (text, _) in QUESTIONS.items()}, "lines": LINES}


def profile(answers: list[tuple[str, bool]]) -> dict:
    """A profile from the three answers: [(question id, yes?)]. Claims are what they said yes to, gaps the rest."""
    yes = [QUESTIONS[q][1] for q, said in answers if said]
    no = [QUESTIONS[q][1] for q, said in answers if not said]
    hard_path = [q for q, _ in answers] == ["python", "web_hard", "data_hard"]
    level = "advanced" if len(yes) == 3 and hard_path else "intermediate" if len(yes) >= 2 else "beginner"
    summary = (f"Has done: {', '.join(yes).lower()}. " if yes else "New to coding. ") + \
              (f"New to: {', '.join(no).lower()}." if no else "")
    return {"done": True, "pending": None, "level": level, "summary": summary.strip(),
            "interview": [{"q": QUESTIONS[q][0], "a": "Yes" if said else "No"} for q, said in answers],
            "claims": [{"skill": s, "said": "Yes", "status": "claimed"} for s in yes], "gaps": no, "wants": []}


if __name__ == "__main__":
    p = profile([("python", True), ("web_hard", False), ("data_easy", True)])
    assert p["level"] == "intermediate" and [c["skill"] for c in p["claims"]] == ["Writing Python functions", "Saving data in a database"]
    assert p["gaps"] == ["Web apps with a login"] and profile([("python", False), ("web_easy", False), ("data_easy", False)])["level"] == "beginner"
    assert profile([("python", True), ("web_hard", True), ("data_hard", True)])["level"] == "advanced"
    assert sum(len(t) for t in LINES.values()) < 600, "keep all the lines within one day's free voice allowance"
    print("onboarding ok,", sum(len(t) for t in LINES.values()), "characters to record")
