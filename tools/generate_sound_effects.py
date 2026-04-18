from __future__ import annotations

from array import array
from dataclasses import dataclass
import json
import math
from pathlib import Path
import random
import wave


SAMPLE_RATE = 44_100
MASTER_GAIN = 0.92
SFX_DIR = Path(__file__).resolve().parents[1] / "dnd_game" / "assets" / "sfx"
README_PATH = SFX_DIR / "README.md"
MANIFEST_PATH = SFX_DIR / "manifest.json"
DICE_ROLL_MIN_SECONDS = 0.40
DICE_ROLL_MAX_SECONDS = 1.75
NOISE_RNG = random.Random(4242)
NOISE_TABLE = [NOISE_RNG.uniform(-1.0, 1.0) for _ in range(65_536)]
NOISE_MASK = len(NOISE_TABLE) - 1


@dataclass(frozen=True, slots=True)
class SoundEffectSpec:
    key: str
    filename: str
    title: str
    duration_seconds: float
    seed: int
    description: str


SOUND_EFFECT_SPECS: tuple[SoundEffectSpec, ...] = (
    SoundEffectSpec(
        "dice_roll_040",
        "dice_roll_040.wav",
        "Quick Dice Tap",
        0.40,
        401,
        "A tight, quick dice tap for minimal rolls.",
    ),
    SoundEffectSpec(
        "dice_roll_070",
        "dice_roll_070.wav",
        "Short Dice Skitter",
        0.70,
        702,
        "A short tabletop dice skitter with a small final stop.",
    ),
    SoundEffectSpec(
        "dice_roll_095",
        "dice_roll_095.wav",
        "Dice Rattle",
        0.95,
        953,
        "A compact rattle of hard dice across wood.",
    ),
    SoundEffectSpec(
        "dice_roll_130",
        "dice_roll_130.wav",
        "Long Dice Tumble",
        1.30,
        1304,
        "A longer tumbling roll with staggered bounces.",
    ),
    SoundEffectSpec(
        "dice_roll_175",
        "dice_roll_175.wav",
        "Extended Dice Roll",
        1.75,
        1755,
        "An extended dice roll that settles at the long animation limit.",
    ),
)


def envelope(index: int, duration_samples: int, attack_ratio: float, release_ratio: float) -> float:
    if duration_samples <= 1:
        return 1.0
    attack = max(1, int(duration_samples * attack_ratio))
    release = max(1, int(duration_samples * release_ratio))
    if index < attack:
        return index / attack
    if index >= duration_samples - release:
        return max(0.0, (duration_samples - index) / release)
    return 1.0


def add_tone(
    buffer: array,
    *,
    start_seconds: float,
    duration_seconds: float,
    frequency: float,
    amplitude: float,
    waveform: str = "sine",
    attack_ratio: float = 0.01,
    release_ratio: float = 0.55,
    pitch_fall: float = 0.0,
) -> None:
    start = int(start_seconds * SAMPLE_RATE)
    total = int(duration_seconds * SAMPLE_RATE)
    phase = 0.0
    for index in range(total):
        destination = start + index
        if destination >= len(buffer):
            break
        time_seconds = index / SAMPLE_RATE
        env = envelope(index, total, attack_ratio, release_ratio)
        current_frequency = max(35.0, frequency - pitch_fall * time_seconds)
        phase += current_frequency / SAMPLE_RATE
        if waveform == "triangle":
            value = 1.0 - 4.0 * abs((phase % 1.0) - 0.5)
        elif waveform == "square":
            value = 1.0 if math.sin(2.0 * math.pi * phase) >= 0.0 else -1.0
        else:
            value = math.sin(2.0 * math.pi * phase)
        buffer[destination] += env * value * amplitude


def add_noise_burst(
    buffer: array,
    *,
    start_seconds: float,
    duration_seconds: float,
    amplitude: float,
    cursor_seed: int,
    attack_ratio: float = 0.02,
    release_ratio: float = 0.75,
    high_pass: float = 0.72,
) -> None:
    start = int(start_seconds * SAMPLE_RATE)
    total = int(duration_seconds * SAMPLE_RATE)
    cursor = cursor_seed & NOISE_MASK
    previous = 0.0
    for index in range(total):
        destination = start + index
        if destination >= len(buffer):
            break
        cursor = (cursor + 53) & NOISE_MASK
        raw = NOISE_TABLE[cursor]
        value = raw - previous * high_pass
        previous = raw
        env = envelope(index, total, attack_ratio, release_ratio)
        buffer[destination] += value * env * amplitude


def add_impact(
    buffer: array,
    *,
    start_seconds: float,
    amplitude: float,
    rng: random.Random,
    heavy: bool = False,
) -> None:
    click_duration = rng.uniform(0.010, 0.024) if not heavy else rng.uniform(0.022, 0.042)
    ring_duration = rng.uniform(0.045, 0.095) if not heavy else rng.uniform(0.075, 0.145)
    cursor_seed = int(start_seconds * SAMPLE_RATE * 19) ^ rng.randrange(1 << 16)
    add_noise_burst(
        buffer,
        start_seconds=start_seconds,
        duration_seconds=click_duration,
        amplitude=amplitude * (0.85 if heavy else 1.0),
        cursor_seed=cursor_seed,
        attack_ratio=0.006,
        release_ratio=0.86,
        high_pass=0.82,
    )
    add_tone(
        buffer,
        start_seconds=start_seconds + rng.uniform(0.000, 0.004),
        duration_seconds=ring_duration,
        frequency=rng.uniform(820.0, 1850.0),
        amplitude=amplitude * rng.uniform(0.30, 0.48),
        waveform="triangle",
        attack_ratio=0.006,
        release_ratio=0.78,
        pitch_fall=rng.uniform(380.0, 900.0),
    )
    add_tone(
        buffer,
        start_seconds=start_seconds + rng.uniform(0.002, 0.008),
        duration_seconds=ring_duration * rng.uniform(0.42, 0.72),
        frequency=rng.uniform(1500.0, 2800.0),
        amplitude=amplitude * rng.uniform(0.12, 0.22),
        waveform="sine",
        attack_ratio=0.01,
        release_ratio=0.66,
        pitch_fall=rng.uniform(700.0, 1400.0),
    )
    if heavy:
        add_tone(
            buffer,
            start_seconds=start_seconds,
            duration_seconds=rng.uniform(0.07, 0.13),
            frequency=rng.uniform(135.0, 220.0),
            amplitude=amplitude * 0.34,
            waveform="sine",
            attack_ratio=0.006,
            release_ratio=0.70,
            pitch_fall=45.0,
        )


def impact_times(duration_seconds: float, rng: random.Random) -> list[float]:
    count = max(4, int(5 + duration_seconds * 10.0))
    latest_rattle = max(0.12, duration_seconds - 0.12)
    times: list[float] = []
    for index in range(count):
        progress = index / max(1, count - 1)
        eased = 1.0 - (1.0 - progress) ** 1.75
        jitter = rng.uniform(-0.030, 0.030) * (1.0 - progress * 0.45)
        times.append(min(latest_rattle, max(0.015, 0.025 + eased * (latest_rattle - 0.035) + jitter)))
    final_stop = max(0.06, duration_seconds - 0.075)
    times.extend([max(0.02, final_stop - rng.uniform(0.045, 0.070)), final_stop])
    return sorted(set(round(value, 4) for value in times if value < duration_seconds - 0.012))


def render_dice_roll(spec: SoundEffectSpec) -> dict[str, object]:
    total_samples = int(round(spec.duration_seconds * SAMPLE_RATE))
    buffer = array("f", [0.0]) * total_samples
    rng = random.Random(spec.seed)
    times = impact_times(spec.duration_seconds, rng)
    for index, start in enumerate(times):
        progress = start / max(spec.duration_seconds, 0.001)
        final_cluster = index >= len(times) - 2
        amplitude = rng.uniform(0.20, 0.34) * (1.0 - progress * 0.36)
        if final_cluster:
            amplitude *= 1.32
        add_impact(buffer, start_seconds=start, amplitude=amplitude, rng=rng, heavy=final_cluster)
        if rng.random() < 0.42 and start + 0.020 < spec.duration_seconds:
            add_impact(
                buffer,
                start_seconds=start + rng.uniform(0.012, 0.035),
                amplitude=amplitude * rng.uniform(0.34, 0.52),
                rng=rng,
                heavy=False,
            )
    add_noise_burst(
        buffer,
        start_seconds=0.0,
        duration_seconds=max(0.08, spec.duration_seconds - 0.05),
        amplitude=0.018,
        cursor_seed=spec.seed * 13,
        attack_ratio=0.10,
        release_ratio=0.92,
        high_pass=0.62,
    )
    peak = max(max(buffer, default=0.0), -min(buffer, default=0.0), 1.0)
    scale = min(MASTER_GAIN / peak, MASTER_GAIN)
    frames = bytearray()
    for sample in buffer:
        value = int(max(-32767, min(32767, round(sample * scale * 32767.0))))
        frames.extend(value.to_bytes(2, byteorder="little", signed=True))
    path = SFX_DIR / spec.filename
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(bytes(frames))
    return {
        "key": spec.key,
        "filename": spec.filename,
        "title": spec.title,
        "duration_seconds": round(spec.duration_seconds, 2),
        "sample_rate": SAMPLE_RATE,
        "description": spec.description,
    }


def remove_existing_sound_effect_files() -> None:
    for path in SFX_DIR.glob("*.wav"):
        path.unlink()


def write_manifest(entries: list[dict[str, object]]) -> None:
    manifest = {
        "sample_rate": SAMPLE_RATE,
        "generator": "tools/generate_sound_effects.py",
        "roll_duration_window_seconds": {
            "minimum": DICE_ROLL_MIN_SECONDS,
            "maximum": DICE_ROLL_MAX_SECONDS,
        },
        "effects": entries,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def write_readme(entries: list[dict[str, object]]) -> None:
    lines = [
        "# Generated Sound Effects",
        "",
        "These WAV files are procedural dice-roll sound effects for gameplay rolls.",
        "Other gameplay sound effects are intentionally absent until they are recreated separately.",
        "",
        f"- Sample rate: `{SAMPLE_RATE} Hz` mono PCM",
        f"- Dice roll duration window: `{DICE_ROLL_MIN_SECONDS:.2f}s` to `{DICE_ROLL_MAX_SECONDS:.2f}s`",
        f"- Effect count: `{len(entries)}`",
        "",
        "## Effects",
        "",
    ]
    for entry in entries:
        lines.append(f"- `{entry['filename']}` | `{entry['key']}` | {entry['duration_seconds']}s")
        lines.append(f"  {entry['description']}")
    README_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    SFX_DIR.mkdir(parents=True, exist_ok=True)
    remove_existing_sound_effect_files()
    entries = [render_dice_roll(spec) for spec in SOUND_EFFECT_SPECS]
    write_manifest(entries)
    write_readme(entries)
    print(f"Generated {len(entries)} dice-roll sound effects in {SFX_DIR}")


if __name__ == "__main__":
    main()
