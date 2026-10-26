"""Records everything Chip says in the first-visit story and onboarding, once, into tutor/static/voice/<id>.mp3.
Same voice as the demo video. Plays instantly, no AI call and no key needed when someone onboards.
    python -m tutor.record_intro           # records the lines that have no clip yet
    python -m tutor.record_intro --again   # records every line again
Needs ELEVEN_LABS_API_KEY in .env."""
import asyncio
import sys
from pathlib import Path

from tutor import llm
from tutor.onboarding import LINES, STORY_LINES

DIR = Path(__file__).parent / "static" / "voice"


async def record(line_id: str, text: str) -> str | None:
    """Records one line. Returns None, or why it couldn't."""
    try:
        audio = await llm.speech(text, direction=None)
    except RuntimeError as err:
        return str(err)[:200]
    if audio[:3] != b"ID3" and not (audio[:1] == b"\xff" and (audio[1] & 0xE0) == 0xE0):
        return "the voice service did not return an mp3"
    (DIR / f"{line_id}.mp3").write_bytes(audio)
    old = DIR / f"{line_id}.wav"
    if old.exists():
        old.unlink()
    return None


async def main(again: bool):
    DIR.mkdir(parents=True, exist_ok=True)
    for line_id, text in {**LINES, **STORY_LINES}.items():
        if (DIR / f"{line_id}.mp3").exists() and not again:
            continue
        problem = await record(line_id, text)
        if problem:
            print(f"Stopped at '{line_id}': {problem}")
            return
        print(f"{line_id}: recorded")
    print("Every line has a clip.")


if __name__ == "__main__":
    asyncio.run(main("--again" in sys.argv))
