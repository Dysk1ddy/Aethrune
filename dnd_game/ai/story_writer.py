from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable

DEFAULT_MODEL = "gpt-5.4"
DEFAULT_REASONING_EFFORT = "minimal"
DEFAULT_MAX_CONTEXT_CHARS = 12_000
DEFAULT_MAX_OUTPUT_TOKENS = 1_800
STORY_WRITER_MODES = ("revision", "dialogue", "scene", "banter")

ACT2_SCENE_KEYS = {
    "act2_claims_council",
    "act2_expedition_hub",
    "conyberry_agatha",
    "neverwinter_wood_survey_camp",
    "stonehollow_dig",
    "glasswater_intake",
    "act2_midpoint_convergence",
    "broken_prospect",
    "south_adit",
    "wave_echo_outer_galleries",
    "black_lake_causeway",
    "forge_of_spells",
    "act2_scaffold_complete",
}


class StoryWriterError(RuntimeError):
    """Raised when the OpenAI-backed writing workflow cannot run."""


@dataclass(frozen=True)
class StoryContextDocument:
    path: Path
    text: str
    truncated: bool
    original_length: int


@dataclass(frozen=True)
class StoryWriterRequest:
    brief: str
    mode: str = "revision"
    title: str | None = None
    scene_key: str | None = None
    speakers: tuple[str, ...] = ()
    tone_notes: str | None = None
    context_paths: tuple[Path, ...] = ()
    model: str = DEFAULT_MODEL
    reasoning_effort: str = DEFAULT_REASONING_EFFORT
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS


@dataclass(frozen=True)
class StoryWriterResult:
    text: str
    model: str
    context_documents: tuple[StoryContextDocument, ...]


def project_root(start: Path | None = None) -> Path:
    candidate = (start or Path(__file__).resolve()).resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for path in (candidate, *candidate.parents):
        if (path / "README.md").exists() and (path / "dnd_game").exists():
            return path
    return Path.cwd().resolve()


def load_local_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        normalized_key = key.strip()
        normalized_value = value.strip().strip('"').strip("'")
        if normalized_key:
            os.environ.setdefault(normalized_key, normalized_value)


def scene_key_is_act2(scene_key: str | None) -> bool:
    if not scene_key:
        return False
    normalized = scene_key.strip().lower()
    return normalized.startswith("act2_") or normalized in ACT2_SCENE_KEYS


def _dedupe_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return tuple(unique)


def default_context_paths(root: Path, scene_key: str | None = None) -> tuple[Path, ...]:
    story_dir = root / "information" / "Story"
    candidates = [story_dir / "STORY_CONTENT_SUMMARY.md"]
    if scene_key:
        if scene_key_is_act2(scene_key):
            candidates.append(story_dir / "ACT2_CONTENT_REFERENCE.md")
        else:
            candidates.append(story_dir / "ACT1_CONTENT_REFERENCE.md")
    return tuple(path.resolve() for path in candidates if path.exists())


def _truncate_text(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0 or len(text) <= max_chars:
        return text, False
    clipped = text[:max_chars]
    if "\n" in clipped:
        clipped = clipped.rsplit("\n", 1)[0]
    return clipped.rstrip(), True


def load_context_documents(paths: Iterable[Path], *, max_chars_per_file: int) -> tuple[StoryContextDocument, ...]:
    documents: list[StoryContextDocument] = []
    for path in _dedupe_paths(paths):
        if not path.exists():
            raise StoryWriterError(f"Context file not found: {path}")
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        trimmed, truncated = _truncate_text(text, max_chars_per_file)
        documents.append(
            StoryContextDocument(
                path=path,
                text=trimmed,
                truncated=truncated,
                original_length=len(text),
            )
        )
    return tuple(documents)


def _mode_output_contract(mode: str) -> str:
    if mode == "dialogue":
        return (
            "Return markdown with two sections: `## Draft` and `## Notes`.\n"
            "In `## Draft`, format spoken lines as `Speaker: line` and player options as bullet points."
        )
    if mode == "scene":
        return (
            "Return markdown with three sections: `## Scene Draft`, `## Dialogue Hooks`, and `## Notes`.\n"
            "Keep scene prose directly usable in a text-adventure scene file."
        )
    if mode == "banter":
        return (
            "Return markdown with two sections: `## Banter` and `## Notes`.\n"
            "Keep each banter line short enough to work as a camp or travel interjection."
        )
    return (
        "Return markdown with two sections: `## Revised Draft` and `## Notes`.\n"
        "Treat the brief as a rewrite request against the supplied source context."
    )


def build_story_writer_instructions(request: StoryWriterRequest) -> str:
    mode = request.mode.strip().lower()
    if mode not in STORY_WRITER_MODES:
        raise StoryWriterError(
            f"Unsupported mode `{request.mode}`. Choose one of: {', '.join(STORY_WRITER_MODES)}."
        )
    base_instructions = [
        "You are a narrative co-writer for Aethrune, a Python text adventure.",
        "Preserve established canon, quest outcomes, route logic, relationship beats, and named-character motivations.",
        "Do not invent new flags, mechanics, quests, locations, or rewards unless the brief explicitly asks for proposals.",
        "Write grounded fantasy prose with clear subtext and distinct voices.",
        "Avoid modern slang, meta commentary, and generic 'AI assistant' phrasing.",
        "Favor dialogue and narration that fit a text-adventure scene implementation.",
    ]
    if request.speakers:
        speakers = ", ".join(request.speakers)
        base_instructions.append(f"Prioritize voice consistency for these speakers: {speakers}.")
    base_instructions.append(_mode_output_contract(mode))
    return "\n".join(base_instructions)


def _relative_label(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def build_story_writer_input(
    request: StoryWriterRequest,
    context_documents: Iterable[StoryContextDocument],
    *,
    root: Path,
) -> str:
    lines = [
        "Project: Aethrune",
        f"Mode: {request.mode}",
        f"Model target: {request.model}",
    ]
    if request.title:
        lines.append(f"Title: {request.title}")
    if request.scene_key:
        lines.append(f"Scene key: {request.scene_key}")
    if request.speakers:
        lines.append(f"Speakers: {', '.join(request.speakers)}")
    if request.tone_notes:
        lines.append(f"Tone notes: {request.tone_notes}")
    lines.extend(
        [
            "",
            "Task brief:",
            request.brief.strip(),
            "",
            "Hard constraints:",
            "- Keep the project canon and gameplay consequences intact.",
            "- Match the tone of the supplied material instead of replacing it with a new setting voice.",
            "- Keep revisions practical for a Python-authored text adventure.",
        ]
    )
    documents = tuple(context_documents)
    if documents:
        lines.extend(["", "Context files:"])
    for document in documents:
        label = _relative_label(document.path, root)
        lines.append("")
        lines.append(f"--- BEGIN CONTEXT: {label} ---")
        if document.truncated:
            lines.append(f"[truncated from {document.original_length} characters]")
        lines.append(document.text)
        lines.append(f"--- END CONTEXT: {label} ---")
    return "\n".join(lines).strip()


class StoryWriterClient:
    def __init__(self, *, root: Path | None = None, env_file: Path | None = None) -> None:
        self.root = project_root(root)
        load_local_env_file(env_file or (self.root / ".env"))

    def resolve_context_paths(
        self,
        request: StoryWriterRequest,
        *,
        include_default_context: bool = True,
    ) -> tuple[Path, ...]:
        paths: list[Path] = []
        if include_default_context:
            paths.extend(default_context_paths(self.root, request.scene_key))
        paths.extend((self.root / path).resolve() if not path.is_absolute() else path.resolve() for path in request.context_paths)
        return _dedupe_paths(paths)

    def create_draft(
        self,
        request: StoryWriterRequest,
        *,
        include_default_context: bool = True,
    ) -> StoryWriterResult:
        if not os.environ.get("OPENAI_API_KEY"):
            raise StoryWriterError(
                "OPENAI_API_KEY is not set. Add it to your environment or a local .env file."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on local environment
            raise StoryWriterError("The `openai` package is not installed. Run `pip install openai`.") from exc

        context_paths = self.resolve_context_paths(
            request,
            include_default_context=include_default_context,
        )
        context_documents = load_context_documents(
            context_paths,
            max_chars_per_file=request.max_context_chars,
        )
        instructions = build_story_writer_instructions(request)
        prompt = build_story_writer_input(request, context_documents, root=self.root)

        response_kwargs = {
            "model": request.model,
            "instructions": instructions,
            "input": prompt,
            "max_output_tokens": request.max_output_tokens,
        }
        if request.reasoning_effort:
            response_kwargs["reasoning"] = {"effort": request.reasoning_effort}

        client = OpenAI()
        response = client.responses.create(**response_kwargs)
        output_text = str(getattr(response, "output_text", "") or "").strip()
        if not output_text:
            raise StoryWriterError("The API call completed but returned no text output.")
        return StoryWriterResult(
            text=output_text,
            model=request.model,
            context_documents=context_documents,
        )
