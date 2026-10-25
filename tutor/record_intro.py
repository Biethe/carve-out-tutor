"""Records Chip's spoken introduction once, as tutor/static/chip-intro.wav, so it plays instantly with no AI call.
One take, at natural speed, pauses kept: stitched pieces and trimmed silences are what make a voice sound artificial.
Run it again after changing INTRO (needs a Groq key with Orpheus' terms accepted):
    python -m tutor.record_intro                  # the chosen voice, into tutor/static/chip-intro.wav
    python -m tutor.record_intro autumn out.wav   # try another voice"""
import asyncio
import sys
import wave
from pathlib import Path

from tutor import llm

# Said the way a person talks: short sentences, a little hesitation, nothing salesy. Under Orpheus' 480 characters.
INTRO = ("Hey, I'm Chip. So, here's how this works. You get an app that already runs. "
         "I take out one small piece... you write it back in... and the app keeps working, on your code. "
         "Bit by bit, more of it becomes yours. "
         "But first, I'd like to get to know you a little. Just a few quick questions, and there are no wrong answers. "
         "Whenever you're ready.")
VOICE = "hannah"
OUT = Path(__file__).parent / "static" / "chip-intro.wav"


def _samples(wav: bytes) -> bytes:
    """The raw sound in a WAV reply (Groq streams it, so the header's length field isn't filled in)."""
    return wav[wav.index(b"data") + 8:]


async def record(voice: str, out: Path):
    for _ in range(10):  # Groq's free plan allows 10 voice requests a minute: wait and retry
        try:
            audio = await llm.speech(INTRO, voice=voice, direction=None)  # no acted cheerfulness: plain and warm
            break
        except RuntimeError as err:
            if "rate_limit" not in str(err):
                raise
            await asyncio.sleep(8)
    else:
        raise RuntimeError("Still rate-limited, try again in a minute.")
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(24000)  # what Orpheus sends
        w.writeframes(_samples(audio))
    with wave.open(str(out)) as check:
        print(f"{out.name} ({voice}): {check.getnframes() / check.getframerate():.1f} s")


if __name__ == "__main__":
    asyncio.run(record(sys.argv[1] if len(sys.argv) > 1 else VOICE, Path(sys.argv[2]) if len(sys.argv) > 2 else OUT))
