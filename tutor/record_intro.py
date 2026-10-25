"""Records everything Chip says during onboarding (tutor/onboarding.py LINES), once, into tutor/static/voice/<id>.wav:
the same voice for every line, plays instantly, no AI call and no key needed when someone onboards.
One natural take per line, at natural speed, with no acted delivery: stitching and speeding up are what sound artificial.
    python -m tutor.record_intro           # records the lines that have no clip yet
    python -m tutor.record_intro --again   # records every line again (after changing the words or the voice)
Needs a Groq key with Orpheus' terms accepted. The free plan allows about 3,600 characters a day: if it runs out,
this stops, says when to try again, and keeps what it recorded."""
import asyncio
import re
import sys
import wave
from pathlib import Path

from tutor import llm
from tutor.onboarding import LINES

VOICE = "hannah"
DIR = Path(__file__).parent / "static" / "voice"


def _samples(wav: bytes) -> bytes:
    """The raw sound in a WAV reply (Groq streams it, so the header's length field isn't filled in)."""
    return wav[wav.index(b"data") + 8:]


async def record(line_id: str, text: str) -> str | None:
    """Records one line. Returns None, or why it couldn't (the daily limit, with when to try again)."""
    for _ in range(8):
        try:
            audio = await llm.speech(text, voice=VOICE, direction=None)
            break
        except RuntimeError as err:
            daily = re.search(r"tokens per day.*?try again in ([\w.]+)", str(err))
            if daily:
                return f"today's voice allowance is used up: try again in {daily[1].rstrip(".")}"
            if "rate_limit" not in str(err):
                raise
            await asyncio.sleep(8)  # the per-minute limit: wait it out
    else:
        return "still rate-limited after a minute"
    with wave.open(str(DIR / f"{line_id}.wav"), "wb") as out:
        out.setnchannels(1), out.setsampwidth(2), out.setframerate(24000)  # what Orpheus sends
        out.writeframes(_samples(audio))
    return None


async def main(again: bool):
    DIR.mkdir(parents=True, exist_ok=True)
    for line_id, text in LINES.items():
        if (DIR / f"{line_id}.wav").exists() and not again:
            continue
        problem = await record(line_id, text)
        if problem:
            print(f"Stopped at '{line_id}': {problem}. Run it again then: it continues where it stopped.")
            return
        print(f"{line_id}: recorded")
    print("Every line has a clip.")


if __name__ == "__main__":
    asyncio.run(main("--again" in sys.argv))
