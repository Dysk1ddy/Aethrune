# OpenAI Story Writer

This project includes an optional OpenAI-backed drafting tool for story work:

- module: `dnd_game/ai/story_writer.py`
- CLI wrapper: `tools/story_writer.py`
- desktop studio: `story_writer_studio.py`
- Windows launcher: `Launch Story Writer Studio.bat`

It is designed as a writing assistant, not as runtime story control. That fits this codebase because scene logic, flags, quest state, route outcomes, and save-sensitive identifiers are authored in Python scene files and data files.

## Retcon Use

The current writing target is the Aethrune retcon.

Use the tool for:

- rewriting legacy scene prose into Aethrune language
- testing NPC voice revisions before editing runtime files
- drafting retcon-safe lore snippets
- creating alternate dialogue options that preserve existing flags and routes
- producing markdown drafts for review before code changes

Do not use model output as source of truth. The active retcon source of truth is:

- `information/Retcon story/Plans/AETHRUNE_RETCON_IMPLEMENTATION_PLAN.md`
- `information/Retcon story/World/`
- `information/Retcon story/NPCs/`
- `information/Retcon story/Systems/`

## Why This Shape

For Aethrune, the safest AI workflow is:

1. Keep plot logic deterministic in code.
2. Let the model draft or revise dialogue and scene prose.
3. Review the draft against the retcon plan.
4. Move only accepted lines into the relevant source file or retcon reference.
5. Run tests after each accepted code change.

This avoids the biggest failure mode of live AI narrative systems in games like this: strong prose that quietly contradicts flags, quest outcomes, companion state, or future scenes.

## Setup

Install the official Python SDK:

```powershell
pip install openai
```

Provide an API key either through your shell or a local `.env` file in the project root.

PowerShell example:

```powershell
setx OPENAI_API_KEY "your_api_key_here"
```

Optional environment variables:

```text
OPENAI_MODEL=gpt-5.4
OPENAI_REASONING_EFFORT=minimal
```

The CLI automatically reads a project-local `.env` file if one exists.

If you prefer a form-based workflow, launch the desktop studio from the project root:

```powershell
python story_writer_studio.py
```

The studio lets you:

- paste or save your `OPENAI_API_KEY`
- choose the model, reasoning level, and rewrite mode
- attach story reference files and scene source files
- write the brief you want to send to `story_writer.py`
- watch the live command output in an embedded console
- review the rewritten text in a dedicated draft pane
- save rewritten markdown with the `Save Draft` button
- optionally install or upgrade `openai` from the same window

The studio currently defaults generated drafts to `information/Story/generated`. During the Aethrune retcon, prefer saving canon-bound drafts under `information/Retcon story/` when you want them to feed the implementation plan.

## Recommended Workflow

- Use `gpt-5.4` when you want the strongest pass on difficult scene rewrites.
- Use `gpt-5.4-mini` when you want faster, cheaper iteration.
- Attach the exact scene file you plan to edit plus the relevant Aethrune retcon markdown.
- Keep briefs concrete: who is speaking, what must stay true, and what emotional effect you want.

Good brief ingredients:

- the scene key or route role
- which NPC voices matter
- what retcon facts must not change
- what should improve: tension, pacing, subtext, clarity, menace, tenderness, or payoff
- which internal IDs must remain untouched

## Example Commands

Revise an implemented scene while keeping the Aethrune Act 1 route map in view:

```powershell
python tools/story_writer.py `
  --mode revision `
  --scene-key blackwake_crossing `
  --title "Blackwake Crossing Aethrune pass" `
  --speaker "Mira Thann" `
  --speaker "Sabra Kestrel" `
  --brief "Rewrite this route-control exchange so it reads as Greywake and Emberway logistics. Preserve existing route logic, flags, and quest outcomes." `
  --context "information/Retcon story/Plans/AETHRUNE_RETCON_IMPLEMENTATION_PLAN.md" `
  --context "information/Retcon story/World/act1_map_system_remap_aethrune.md" `
  --context dnd_game/gameplay/story_intro.py `
  --save "information/Retcon story/Lore/generated/blackwake_aethrune_pass.md"
```

Draft a fresh camp banter packet:

```powershell
python tools/story_writer.py `
  --mode banter `
  --speaker "Elira Lanternward" `
  --speaker "Bryn Underbough" `
  --brief "Write 6 short campfire lines after a costly Emberway fight. Keep Bryn defensive and Elira steady without making either sentimental." `
  --context "information/Retcon story/NPCs/NPC_relationship_map.md" `
  --context "information/Retcon story/World/act1_map_system_remap_aethrune.md"
```

Draft a new lore note:

```powershell
python tools/story_writer.py `
  --mode lore `
  --title "Meridian Accord roadside relay" `
  --brief "Draft a compact lore note explaining how old Meridian relay stations shape modern route control without revealing Act 3 secrets." `
  --context "information/Retcon story/World/aethrune_world_v1.md" `
  --context "information/Retcon story/Lore/aethrune_v2_world.md"
```

## Notes On Defaults

If you pass a `--scene-key`, the tool may automatically add legacy story-summary context when available.

You can disable default context with:

```powershell
--no-default-context
```

For retcon work, use `--no-default-context` when old references are distracting and provide only the Aethrune files you want.

## Best Practices For This Repo

- Treat generated text as draft material, not source of truth.
- Keep gameplay effects in Python and data files, not in model output.
- When revising an existing scene, include the actual source file as context.
- When inventing new content, route the first pass into `information/Retcon story/` before moving it into runtime code.
- Preserve internal scene IDs, quest IDs, save keys, and flags unless an implementation plan explicitly says migration code is ready.
- After accepting a draft into code, run the relevant tests.

Core test:

```powershell
python -m pytest tests/test_core.py
```

Focused smoke test:

```powershell
python -m pytest -m smoke
```
