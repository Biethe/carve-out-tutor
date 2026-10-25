"""Records Chip's spoken introduction once, as tutor/static/chip-intro.wav, so it plays instantly with no AI call.
Run it again after changing INTRO (needs a Groq key with Orpheus' terms accepted): python -m tutor.record_intro"""
import asyncio
import wave
from pathlib import Path

from tutor import llm

# Short and upbeat. The [excited]/[cheerful] directions shape Orpheus' delivery; they aren't read out.
INTRO = [
    "[excited] Hey! I'm Chip, your coding sidekick!",
    "[cheerful] Here's the deal. You get a real app that already works. I snip out one piece, you code it back in,",
    "[excited] and boom, the app runs on your code!",
    "[cheerful] Piece by piece, the whole thing becomes yours.",
    "[cheerful] But first, I want to get to know you. A few quick questions, no wrong answers.",
    "[excited] Ready? Let's go!",
]
OUT = Path(__file__).parent / "static" / "chip-intro.wav"


PAUSE = b"\0\0" * int(24000 * 0.12)  # a short breath between pieces


def _samples(wav: bytes) -> bytes:
    """The raw sound in a WAV reply (Groq streams it, so the header's length field isn't filled in),
    with the silence trimmed from both ends, so the pieces flow without dead air."""
    pcm = wav[wav.index(b"data") + 8:]
    loud = [i for i in range(0, len(pcm) - 1, 2) if abs(int.from_bytes(pcm[i:i + 2], "little", signed=True)) > 600]
    return pcm[max(0, loud[0] - 2400):loud[-1] + 2400] if loud else pcm  # keep 50 ms around the speech


async def _say(line: str) -> bytes:
    for _ in range(10):  # Groq's free plan allows 10 voice requests a minute: wait and retry
        try:
            return await llm.speech(line)
        except RuntimeError as err:
            if "rate_limit" not in str(err):
                raise
            await asyncio.sleep(8)
    raise RuntimeError("Still rate-limited, try again in a minute.")


async def main():
    parts = [await _say(line) for line in INTRO]
    with wave.open(str(OUT), "wb") as out:
        out.setnchannels(1), out.setsampwidth(2), out.setframerate(24000)  # what Orpheus sends
        out.writeframes(PAUSE.join(_samples(part) for part in parts))
    with wave.open(str(OUT)) as check:
        print(f"{OUT.name}: {check.getnframes() / check.getframerate():.1f} s")


if __name__ == "__main__":
    asyncio.run(main())
