from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dnd_game.ai.story_writer import (
    DEFAULT_MAX_CONTEXT_CHARS,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    STORY_WRITER_MODES,
    StoryWriterClient,
    StoryWriterError,
    StoryWriterRequest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Draft or revise Aethrune story text with the OpenAI API.",
    )
    parser.add_argument("--brief", required=True, help="What you want the model to write or revise.")
    parser.add_argument(
        "--mode",
        default="revision",
        choices=STORY_WRITER_MODES,
        help="The kind of writing pass to request.",
    )
    parser.add_argument("--title", help="Optional title for the requested draft.")
    parser.add_argument("--scene-key", help="Optional scene key to help pick the right default story reference.")
    parser.add_argument(
        "--speaker",
        dest="speakers",
        action="append",
        default=[],
        help="Named speaker to keep in voice. Repeat this flag for multiple speakers.",
    )
    parser.add_argument("--tone", dest="tone_notes", help="Optional tone or style notes.")
    parser.add_argument(
        "--context",
        dest="context_paths",
        action="append",
        default=[],
        help="Extra context file to include. Repeat this flag for multiple files.",
    )
    parser.add_argument(
        "--no-default-context",
        action="store_true",
        help="Use only explicitly provided context files.",
    )
    parser.add_argument("--model", help="OpenAI model to use.")
    parser.add_argument(
        "--reasoning-effort",
        help="Responses API reasoning effort, for example `minimal`, `low`, or `medium`.",
    )
    parser.add_argument(
        "--max-context-chars",
        type=int,
        default=DEFAULT_MAX_CONTEXT_CHARS,
        help="Maximum characters to read from each context file.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=DEFAULT_MAX_OUTPUT_TOKENS,
        help="Upper bound for generated output tokens.",
    )
    parser.add_argument(
        "--save",
        type=Path,
        help="Optional path to write the generated draft.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = StoryWriterClient()
    request = StoryWriterRequest(
        brief=args.brief,
        mode=args.mode,
        title=args.title,
        scene_key=args.scene_key,
        speakers=tuple(args.speakers),
        tone_notes=args.tone_notes,
        context_paths=tuple(Path(path) for path in args.context_paths),
        model=args.model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL),
        reasoning_effort=args.reasoning_effort
        or os.environ.get("OPENAI_REASONING_EFFORT", DEFAULT_REASONING_EFFORT),
        max_context_chars=args.max_context_chars,
        max_output_tokens=args.max_output_tokens,
    )
    try:
        result = client.create_draft(
            request,
            include_default_context=not args.no_default_context,
        )
    except StoryWriterError as exc:
        print(f"Story writer setup error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - depends on live API/network
        print(f"Story writer request failed: {exc}", file=sys.stderr)
        return 1

    if args.save is not None:
        destination = args.save if args.save.is_absolute() else client.root / args.save
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(result.text + "\n", encoding="utf-8")

    print(result.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
