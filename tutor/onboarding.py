"""First-launch onboarding: three yes/no questions from a fixed tree, every line pre-recorded in Chip's voice.
No AI and no key needed, so it's instant and sounds the same for everyone. (Improve my profile, later, uses the AI.)
Q1 is about writing functions (in any language); Q2 about the web, harder after a yes and easier after a no; Q3 about data, the same way."""

# id: (what Chip says, the skill a yes shows)
QUESTIONS = {
    "python": ("Have you written your own functions before, in any language?", "Writing functions"),
    "web_hard": ("Have you built a web app with a login form?", "Web apps with a login"),
    "web_easy": ("Have you made a web page before?", "Making web pages"),
    "data_hard": ("Have you stored passwords safely, with hashing?", "Password hashing"),
    "data_easy": ("Have you saved data in a database before?", "Saving data in a database"),
}
# Everything Chip says during onboarding, recorded once (tutor/record_intro.py): clip id -> words.
# Upbeat on purpose: it's a welcome. The spoken questions get a little lead-in that stays off the screen.
LEAD_IN = {"python": "Okay! ", "data_hard": "Last one! ", "data_easy": "Last one! "}
LINES = {
    "intro": "Hey, welcome! I'm Chip! You're about to rebuild pieces of a real app, and watch it keep running on your code. "
             "Three quick yes or no questions, and we're off!",
    **{qid: LEAD_IN.get(qid, "") + text for qid, (text, _) in QUESTIONS.items()},
    "yes": "Nice!",
    "no": "No problem at all!",
    "again": "Oops, I missed that! Was it a yes, or a no?",
    "closing": "Awesome, that's all I need! Let's build!",
}

# The first-visit story (tutor/static/story.js), one clip per beat, said the way the screen shows it.
STORY_LINES = {
    "story1": "Hi, I'm Chip! Ever wanted to know how a big project really works?",
    "story2": "You have its source code. Hundreds of files. Where do you even start?",
    "story3": "Bring it here, and it keeps working, just like before.",
    "story4": "Inside, it's small pieces of code, called functions, spread over many files.",
    "story5": "I take one piece out, at your level, and you write it back. I give hints, never answers.",
    "story6": "Checks prove your piece works exactly like the original, so nothing breaks.",
    "story7": "Piece by piece, the whole system becomes yours. So, which project will you take apart?",
}

def tree() -> dict:
    """What the page needs: the first question, and which question follows a yes or a no."""
    return {"first": "python", "next": {"python": ["web_hard", "web_easy"], "web_hard": ["data_hard", "data_easy"],
                                        "web_easy": ["data_hard", "data_easy"]},
            "questions": {qid: text for qid, (text, _) in QUESTIONS.items()}, "lines": LINES}  # the screen shows no lead-in


def profile(answers: list[tuple[str, bool]]) -> dict:
    """A profile from the three answers: [(question id, yes?)]. Claims are what they said yes to, gaps the rest."""
    yes = [QUESTIONS[q][1] for q, said in answers if said]
    no = [QUESTIONS[q][1] for q, said in answers if not said]
    hard_path = [q for q, _ in answers] == ["python", "web_hard", "data_hard"]
    level = "advanced" if len(yes) == 3 and hard_path else "intermediate" if len(yes) >= 2 else "beginner"
    summary = (f"Has done: {', '.join(yes).lower()}. " if yes else "New to coding. ") + \
              (f"New to: {', '.join(no).lower()}." if no else "")
    if not answers:  # they skipped the questions
        summary = "Skipped the first questions."
    return {"done": True, "pending": None, "level": level, "summary": summary.strip(),
            "interview": [{"q": QUESTIONS[q][0], "a": "Yes" if said else "No"} for q, said in answers],
            "claims": [{"skill": s, "said": "Yes", "status": "claimed"} for s in yes], "gaps": no, "wants": []}


if __name__ == "__main__":
    p = profile([("python", True), ("web_hard", False), ("data_easy", True)])
    assert p["level"] == "intermediate" and [c["skill"] for c in p["claims"]] == ["Writing functions", "Saving data in a database"]
    assert p["gaps"] == ["Web apps with a login"] and profile([("python", False), ("web_easy", False), ("data_easy", False)])["level"] == "beginner"
    assert profile([("python", True), ("web_hard", True), ("data_hard", True)])["level"] == "advanced"
    skipped = profile([])
    assert skipped["done"] and skipped["level"] == "beginner" and skipped["summary"] == "Skipped the first questions." and not skipped["claims"]
    assert sum(len(t) for t in LINES.values()) < 600, "keep all the lines within one day's free voice allowance"
    print("onboarding ok,", sum(len(t) for t in LINES.values()), "characters to record")
