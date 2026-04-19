from __future__ import annotations

import re
from typing import Any

from .engine import available_travel_edges, current_room_exits, requirement_met, room_exit_directions, room_travel_path
from .models import DraftMapState, DungeonMap, DungeonRoom, HybridMapBlueprint, TravelNode

try:
    from rich import box
    from rich.align import Align
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    Console = Any  # type: ignore[assignment]
    Group = None
    Panel = None
    Table = None
    Text = Any  # type: ignore[assignment]
    box = None
    Align = None
    RICH_AVAILABLE = False


ROLE_SYMBOLS = {
    "entrance": "D",
    "combat": "E",
    "event": "*",
    "treasure": "T",
    "boss": "B",
    "exit": "X",
}

DIRECTION_ORDER = {
    "NORTH": 0,
    "EAST": 2,
    "SOUTH": 4,
    "WEST": 6,
    "HERE": 8,
}


def _direction_sort_key(direction: str) -> tuple[int, ...]:
    return tuple(DIRECTION_ORDER.get(part, 99) for part in direction.split("-"))


def _room_target_sort_key(from_room: DungeonRoom, to_room: DungeonRoom, direction: str) -> tuple[int, tuple[int, ...]]:
    dx = to_room.x - from_room.x
    dy = to_room.y - from_room.y
    if dy < 0:
        primary = DIRECTION_ORDER["NORTH"]
    elif dy > 0:
        primary = DIRECTION_ORDER["SOUTH"]
    elif dx > 0:
        primary = DIRECTION_ORDER["EAST"]
    elif dx < 0:
        primary = DIRECTION_ORDER["WEST"]
    else:
        primary = DIRECTION_ORDER["HERE"]
    return (primary, _direction_sort_key(direction))

ACT2_METRIC_LABELS = {
    "act2_town_stability": ("Fractured", "Shaken", "Strained", "Holding", "Steady", "United"),
    "act2_route_control": ("Lost", "Thin", "Contested", "Firm", "Dominant", "Commanding"),
    "act2_whisper_pressure": ("Quieted", "Faint", "Present", "Growing", "Severe", "Overwhelming"),
}

ACT2_SPONSOR_LABELS = {
    "exchange": "Halia's Exchange bloc",
    "lionshield": "Linene's supply line",
    "wardens": "Elira and Daran's wardens",
    "council": "a divided council",
}

ACT2_LATE_ROUTE_LABELS = {
    "broken_prospect": "Broken Prospect first",
    "south_adit": "South Adit first",
}

ACT2_CAPTIVE_LABELS = {
    "captives_endangered": "Endangered",
    "few_saved": "Few saved",
    "many_saved": "Many saved",
    "uncertain": "Uncertain",
}


def _box_panel(title: str, lines: list[str], width: int = 62) -> str:
    inner_width = max(width - 4, len(title) + 2, *(len(line) for line in lines or [""]))
    top = f"+- {title} " + "-" * max(0, inner_width - len(title) - 2) + "+"
    body = [f"| {line.ljust(inner_width)} |" for line in lines] or [f"| {' ' * inner_width} |"]
    bottom = f"+{'-' * (inner_width + 2)}+"
    return "\n".join([top, *body, bottom])


def _int_flag(flag_values: dict[str, Any], key: str, default: int = 0) -> int:
    value = flag_values.get(key, default)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float):
        return int(value)
    return default


def _act2_metric_line(flag_values: dict[str, Any], key: str, label: str) -> str:
    value = max(0, min(5, _int_flag(flag_values, key, 0)))
    return f"{label}: {ACT2_METRIC_LABELS[key][value]} ({value}/5)"


def _act2_pressure_lines(flag_values: dict[str, Any]) -> list[str]:
    sponsor_key = str(flag_values.get("act2_sponsor", "council"))
    route_key = str(flag_values.get("act2_first_late_route", ""))
    captive_key = str(flag_values.get("act2_captive_outcome", "uncertain"))
    neglected = str(flag_values.get("act2_neglected_lead", "")).strip()
    lines = [
        _act2_metric_line(flag_values, "act2_town_stability", "Town Stability"),
        _act2_metric_line(flag_values, "act2_route_control", "Route Control"),
        _act2_metric_line(flag_values, "act2_whisper_pressure", "Whisper Pressure"),
        f"Sponsor: {ACT2_SPONSOR_LABELS.get(sponsor_key, sponsor_key or 'Uncommitted')}",
        f"Late-route priority: {ACT2_LATE_ROUTE_LABELS.get(route_key, 'Unchosen')}",
        f"Captives: {ACT2_CAPTIVE_LABELS.get(captive_key, captive_key.replace('_', ' ').title() or 'Uncertain')}",
    ]
    if neglected and neglected != "none":
        resolved = bool(flag_values.get(neglected))
        label = neglected.replace("_", " ").title()
        lines.append(f"Delayed lead: {label} ({'recovered' if resolved else 'unresolved'})")
    return lines


def build_act2_pressure_panel_text(flag_values: dict[str, Any]) -> str:
    return _box_panel("Act II Pressures", _act2_pressure_lines(flag_values), width=78)


def build_act2_pressure_panel(flag_values: dict[str, Any]) -> Panel:
    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(ratio=2)
    table.add_column(ratio=2)

    metrics = Table.grid(expand=True)
    metrics.add_column(ratio=2)
    metrics.add_column(ratio=1, justify="right")
    for key, label in (
        ("act2_town_stability", "Town Stability"),
        ("act2_route_control", "Route Control"),
        ("act2_whisper_pressure", "Whisper Pressure"),
    ):
        value = max(0, min(5, _int_flag(flag_values, key, 0)))
        metrics.add_row(Text(label, style="cyan"), Text(f"{ACT2_METRIC_LABELS[key][value]} {value}/5", style="white"))

    sponsor_key = str(flag_values.get("act2_sponsor", "council"))
    route_key = str(flag_values.get("act2_first_late_route", ""))
    captive_key = str(flag_values.get("act2_captive_outcome", "uncertain"))
    statuses = Table.grid(expand=True)
    statuses.add_column(ratio=2)
    statuses.add_column(ratio=2)
    statuses.add_row(Text("Sponsor", style="cyan"), Text(ACT2_SPONSOR_LABELS.get(sponsor_key, sponsor_key or "Uncommitted"), style="white"))
    statuses.add_row(Text("Late Route", style="cyan"), Text(ACT2_LATE_ROUTE_LABELS.get(route_key, "Unchosen"), style="white"))
    statuses.add_row(
        Text("Captives", style="cyan"),
        Text(ACT2_CAPTIVE_LABELS.get(captive_key, captive_key.replace("_", " ").title() or "Uncertain"), style="white"),
    )

    table.add_row(
        Panel(metrics, title="Pressure", border_style="yellow", box=box.SIMPLE),
        Panel(statuses, title="Status", border_style="cyan", box=box.SIMPLE),
    )
    return Panel(table, title="Act II Pressures", border_style="yellow", box=box.ROUNDED, padding=(0, 1))


def _node_is_known(node: TravelNode, state: DraftMapState) -> bool:
    return node.node_id == state.current_node_id or node.node_id in state.visited_nodes


def _hidden_node_label(node: TravelNode) -> str:
    return "?" * len(node.short_label)


def _node_inner_width(blueprint: HybridMapBlueprint) -> int:
    return max(len(node.short_label) for node in blueprint.nodes.values()) + 2


def _node_label(node: TravelNode, state: DraftMapState) -> str:
    if _node_is_known(node, state):
        return node.short_label
    return _hidden_node_label(node)


def _node_status(node: TravelNode, state: DraftMapState) -> str:
    if node.node_id == state.current_node_id:
        return "Current"
    if node.node_id in state.visited_nodes:
        return "Explored"
    if requirement_met(state, node.requirement):
        return "Unexplored"
    return "Unknown"


def _node_card_token(node: TravelNode, blueprint: HybridMapBlueprint, state: DraftMapState) -> str:
    label = _node_label(node, state).center(_node_inner_width(blueprint))
    if node.node_id == state.current_node_id:
        return f"({label})"
    return f"[{label}]"


def _node_style(node: TravelNode, state: DraftMapState) -> str:
    if node.node_id == state.current_node_id:
        return "bold black on bright_cyan"
    if node.node_id in state.visited_nodes:
        return "bold green"
    if requirement_met(state, node.requirement):
        return "dim"
    return "dim"


def _unknown_travel_count(blueprint: HybridMapBlueprint, state: DraftMapState) -> int:
    return sum(
        1
        for edge in available_travel_edges(blueprint, state)
        if not _node_is_known(blueprint.nodes[edge.to_node_id], state)
    )


_OVERWORLD_NODE_PATTERN = re.compile(r"\{([^}]+)\}")
_OVERWORLD_X_SPACING = 20
_OVERWORLD_Y_SPACING = 2
_OVERWORLD_PADDING = 2
_OVERWORLD_SIDEBAR_WIDTH = 30


def _render_overworld_template_line(blueprint: HybridMapBlueprint, state: DraftMapState, row: str) -> str:
    rendered: list[str] = []
    cursor = 0
    for match in _OVERWORLD_NODE_PATTERN.finditer(row):
        rendered.append(row[cursor : match.start()])
        node = blueprint.nodes.get(match.group(1))
        if node is None:
            rendered.append(match.group(0))
        else:
            token = _node_card_token(node, blueprint, state)
            rendered.append(token.center(max(len(match.group(0)), len(token))))
        cursor = match.end()
    rendered.append(row[cursor:])
    return "".join(rendered).rstrip()


def _render_overworld_template_line_rich(blueprint: HybridMapBlueprint, state: DraftMapState, row: str) -> Text:
    rendered = Text()
    cursor = 0
    for match in _OVERWORLD_NODE_PATTERN.finditer(row):
        if match.start() > cursor:
            rendered.append(row[cursor : match.start()], style="dim")
        node = blueprint.nodes.get(match.group(1))
        if node is None:
            rendered.append(match.group(0), style="dim")
        else:
            token = _node_card_token(node, blueprint, state)
            field_width = max(len(match.group(0)), len(token))
            left_padding = (field_width - len(token)) // 2
            right_padding = field_width - len(token) - left_padding
            if left_padding:
                rendered.append(" " * left_padding, style="dim")
            rendered.append(token, style=_node_style(node, state))
            if right_padding:
                rendered.append(" " * right_padding, style="dim")
        cursor = match.end()
    if cursor < len(row):
        rendered.append(row[cursor:], style="dim")
    return rendered


def _overworld_position_centers(blueprint: HybridMapBlueprint) -> dict[str, tuple[int, int]]:
    if not blueprint.overworld_positions:
        return {}
    token_width = _node_inner_width(blueprint) + 2
    min_x = min(x for x, _ in blueprint.overworld_positions.values())
    min_y = min(y for _, y in blueprint.overworld_positions.values())
    return {
        node_id: (
            _OVERWORLD_PADDING + (x - min_x) * _OVERWORLD_X_SPACING + token_width // 2,
            (y - min_y) * _OVERWORLD_Y_SPACING,
        )
        for node_id, (x, y) in blueprint.overworld_positions.items()
    }


def _put_overworld_connector(canvas: list[list[str]], x: int, y: int, glyph: str) -> None:
    if y < 0 or y >= len(canvas) or x < 0 or x >= len(canvas[y]):
        return
    current = canvas[y][x]
    if current == " " or current == glyph:
        canvas[y][x] = glyph
    elif current in {"|", "-"} and glyph in {"|", "-"}:
        canvas[y][x] = "+"
    elif current != "+":
        canvas[y][x] = "+"


def _draw_overworld_horizontal(canvas: list[list[str]], y: int, x1: int, x2: int) -> None:
    start, end = sorted((x1, x2))
    for x in range(start, end + 1):
        _put_overworld_connector(canvas, x, y, "-")


def _draw_overworld_vertical(canvas: list[list[str]], x: int, y1: int, y2: int) -> None:
    start, end = sorted((y1, y2))
    for y in range(start, end + 1):
        _put_overworld_connector(canvas, x, y, "|")


def _draw_overworld_edge(canvas: list[list[str]], source: tuple[int, int], target: tuple[int, int]) -> None:
    source_x, source_y = source
    target_x, target_y = target
    if source_y == target_y:
        _draw_overworld_horizontal(canvas, source_y, source_x, target_x)
        return
    if source_x == target_x:
        _draw_overworld_vertical(canvas, source_x, source_y + 1, target_y - 1)
        return

    upper_y = min(source_y, target_y)
    lower_y = max(source_y, target_y)
    mid_y = upper_y + max(1, (lower_y - upper_y) // 2)
    _draw_overworld_vertical(canvas, source_x, source_y + 1, mid_y)
    _put_overworld_connector(canvas, source_x, mid_y, "+")
    _draw_overworld_horizontal(canvas, mid_y, source_x, target_x)
    _put_overworld_connector(canvas, target_x, mid_y, "+")
    _draw_overworld_vertical(canvas, target_x, mid_y + 1, target_y - 1)


def _coordinate_overworld_card_lines(blueprint: HybridMapBlueprint, state: DraftMapState) -> list[str]:
    centers = _overworld_position_centers(blueprint)
    if not centers:
        return []
    token_width = _node_inner_width(blueprint) + 2
    half_token = token_width // 2
    width = max(center_x + half_token + _OVERWORLD_PADDING for center_x, _ in centers.values())
    height = max(center_y for _, center_y in centers.values()) + 1
    canvas = [[" "] * width for _ in range(height)]

    for edge in blueprint.edges:
        if edge.from_node_id in centers and edge.to_node_id in centers:
            _draw_overworld_edge(canvas, centers[edge.from_node_id], centers[edge.to_node_id])

    for node_id, (center_x, center_y) in centers.items():
        node = blueprint.nodes[node_id]
        token = _node_card_token(node, blueprint, state)
        left = center_x - len(token) // 2
        for offset, char in enumerate(token):
            column = left + offset
            if 0 <= column < width:
                canvas[center_y][column] = char

    return ["".join(row) for row in canvas]


def _coordinate_overworld_card_lines_rich(blueprint: HybridMapBlueprint, state: DraftMapState) -> list[Text]:
    lines = _coordinate_overworld_card_lines(blueprint, state)
    if not lines:
        return []
    centers = _overworld_position_centers(blueprint)
    rich_lines = [
        Text(line, style="dim", no_wrap=True, overflow="crop") for line in lines
    ]
    for node_id, (center_x, center_y) in centers.items():
        if center_y >= len(rich_lines):
            continue
        token = _node_card_token(blueprint.nodes[node_id], blueprint, state)
        start = max(0, center_x - len(token) // 2)
        end = min(len(rich_lines[center_y]), start + len(token))
        rich_lines[center_y].stylize(_node_style(blueprint.nodes[node_id], state), start, end)
    return rich_lines


def _sidebar_wrap(line: str, *, width: int = _OVERWORLD_SIDEBAR_WIDTH) -> list[str]:
    if len(line) <= width:
        return [line]
    words = line.split()
    wrapped: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
            continue
        if current:
            wrapped.append(current)
        current = word
    if current:
        wrapped.append(current)
    return wrapped or [line[:width]]


def _overworld_edge_label(edge, target: TravelNode) -> str:
    if target.title not in edge.label and target.title.lower() in edge.label.lower():
        return f"{edge.label} ({target.title})"
    return edge.label


def _overworld_travel_lines(blueprint: HybridMapBlueprint, state: DraftMapState) -> list[str]:
    edges = available_travel_edges(blueprint, state)
    known_edges = [edge for edge in edges if _node_is_known(blueprint.nodes[edge.to_node_id], state)]
    unknown_edge_count = _unknown_travel_count(blueprint, state)
    lines: list[str] = []
    if known_edges:
        for edge in known_edges:
            label = _overworld_edge_label(edge, blueprint.nodes[edge.to_node_id])
            for index, wrapped in enumerate(_sidebar_wrap(label, width=_OVERWORLD_SIDEBAR_WIDTH - 2)):
                lines.append(f"- {wrapped}" if index == 0 else f"  {wrapped}")
    if unknown_edge_count:
        text = f"{unknown_edge_count} unexplored route(s) branch from here"
        for index, wrapped in enumerate(_sidebar_wrap(text, width=_OVERWORLD_SIDEBAR_WIDTH - 2)):
            lines.append(f"- {wrapped}" if index == 0 else f"  {wrapped}")
    if not lines:
        lines.append("- No unlocked travel from here")
    return lines


def _overworld_location_lines(blueprint: HybridMapBlueprint, state: DraftMapState) -> list[str]:
    current_node = blueprint.nodes.get(state.current_node_id)
    known_nodes = [node for node in blueprint.nodes.values() if _node_is_known(node, state)]
    hidden_count = len(blueprint.nodes) - len(known_nodes)
    lines = [f"Current: {current_node.title if current_node is not None else 'Unknown'}"]
    lines.append(f"Known: {len(known_nodes)}/{len(blueprint.nodes)}")
    if hidden_count > 0:
        lines.append(f"Hidden: {hidden_count}")
    return [wrapped for line in lines for wrapped in _sidebar_wrap(line)]


def _overworld_sidebar_lines(blueprint: HybridMapBlueprint, state: DraftMapState) -> list[str]:
    lines = [
        "Route Key",
        "---------",
        "( NAME ) Current",
        "[ NAME ] Explored",
        "[ ????? ] Hidden",
        "",
        "Travel",
        "------",
    ]
    lines.extend(_overworld_travel_lines(blueprint, state))
    lines.extend(["", "Location", "--------"])
    lines.extend(_overworld_location_lines(blueprint, state))
    return lines


def _combine_overworld_map_and_sidebar(map_lines: list[str], sidebar_lines: list[str]) -> list[str]:
    map_width = max((len(line) for line in map_lines), default=0)
    row_count = max(len(map_lines), len(sidebar_lines))
    combined: list[str] = []
    for index in range(row_count):
        map_line = map_lines[index] if index < len(map_lines) else ""
        sidebar_line = sidebar_lines[index] if index < len(sidebar_lines) else ""
        if sidebar_line:
            combined.append(f"{map_line.ljust(map_width)}    {sidebar_line}")
        else:
            combined.append(map_line.ljust(map_width))
    return combined


def _overworld_node_levels(blueprint: HybridMapBlueprint) -> list[list[TravelNode]]:
    levels: list[list[TravelNode]] = []
    for row in blueprint.overworld_template:
        node_ids = re.findall(r"\{([^}]+)\}", row)
        if not node_ids:
            continue
        levels.append([blueprint.nodes[node_id] for node_id in node_ids])
    return levels


def _row_positions(count: int, *, width: int, token_width: int, gap: int = 7) -> list[int]:
    total_width = count * token_width + max(0, count - 1) * gap
    left = max(0, (width - total_width) // 2)
    return [left + index * (token_width + gap) for index in range(count)]


def _render_card_row(nodes: list[TravelNode], *, blueprint: HybridMapBlueprint, state: DraftMapState, width: int) -> str:
    token_width = _node_inner_width(blueprint) + 2
    line = [" "] * width
    for position, node in zip(_row_positions(len(nodes), width=width, token_width=token_width), nodes):
        token = _node_card_token(node, blueprint, state)
        line[position : position + len(token)] = list(token)
    return "".join(line).rstrip()


def _render_card_row_rich(nodes: list[TravelNode], *, blueprint: HybridMapBlueprint, state: DraftMapState, width: int) -> Text:
    token_width = _node_inner_width(blueprint) + 2
    line = Text()
    cursor = 0
    for position, node in zip(_row_positions(len(nodes), width=width, token_width=token_width), nodes):
        if position > cursor:
            line.append(" " * (position - cursor), style="dim")
        token = _node_card_token(node, blueprint, state)
        line.append(token, style=_node_style(node, state))
        cursor = position + len(token)
    if cursor < width:
        line.append(" " * (width - cursor), style="dim")
    return line


def _render_connection_lines(
    blueprint: HybridMapBlueprint,
    current_nodes: list[TravelNode],
    next_nodes: list[TravelNode],
    *,
    width: int,
) -> list[str]:
    token_width = _node_inner_width(blueprint) + 2
    current_positions = _row_positions(len(current_nodes), width=width, token_width=token_width)
    next_positions = _row_positions(len(next_nodes), width=width, token_width=token_width)
    current_centers = [position + token_width // 2 for position in current_positions]
    next_centers = [position + token_width // 2 for position in next_positions]

    def make_line(*marks: tuple[int, str]) -> str:
        line = [" "] * width
        for column, glyph in marks:
            if 0 <= column < width:
                line[column] = glyph
        return "".join(line).rstrip()

    if len(current_nodes) == 1 and len(next_nodes) == 1:
        return [make_line((current_centers[0], "|"))]
    if len(current_nodes) == 1 and len(next_nodes) > 1:
        source = current_centers[0]
        branch_marks = [((source + target) // 2, "/" if target < source else "\\") for target in next_centers]
        return [make_line((source, "|")), make_line(*branch_marks)]
    if len(current_nodes) > 1 and len(next_nodes) == 1:
        target = next_centers[0]
        merge_marks = [((source + target) // 2, "\\" if source < target else "/") for source in current_centers]
        return [make_line(*merge_marks), make_line((target, "|"))]
    return [make_line(*[(center, "|") for center in current_centers])]


def _overworld_card_lines(blueprint: HybridMapBlueprint, state: DraftMapState) -> list[str]:
    return _coordinate_overworld_card_lines(blueprint, state) or [
        _render_overworld_template_line(blueprint, state, row) for row in blueprint.overworld_template
    ]


def _overworld_card_lines_rich(blueprint: HybridMapBlueprint, state: DraftMapState) -> list[Text]:
    return _coordinate_overworld_card_lines_rich(blueprint, state) or [
        _render_overworld_template_line_rich(blueprint, state, row) for row in blueprint.overworld_template
    ]


def _directional_exit_lines(dungeon: DungeonMap, state: DraftMapState) -> list[str]:
    room = dungeon.rooms[state.current_room_id or dungeon.entrance_room_id]
    exits = current_room_exits(dungeon, state)
    if not exits:
        return ["- None"]
    directions = room_exit_directions(room, exits, dungeon=dungeon)
    ordered_exits = sorted(exits, key=lambda exit_room: (_room_target_sort_key(room, exit_room, directions[exit_room.room_id]), exit_room.title))
    return [f"- {directions[exit_room.room_id]} -> {exit_room.title}" for exit_room in ordered_exits]


def _directional_exit_text(dungeon: DungeonMap, state: DraftMapState) -> str:
    room = dungeon.rooms[state.current_room_id or dungeon.entrance_room_id]
    exits = current_room_exits(dungeon, state)
    if not exits:
        return "None"
    directions = room_exit_directions(room, exits, dungeon=dungeon)
    ordered_exits = sorted(exits, key=lambda exit_room: (_room_target_sort_key(room, exit_room, directions[exit_room.room_id]), exit_room.title))
    return ", ".join(f"{directions[exit_room.room_id]} -> {exit_room.title}" for exit_room in ordered_exits)


def build_hud_panel_text(
    *,
    player_name: str = "Draft Hero",
    hp_text: str = "34/40",
    gold: int = 27,
    quest_text: str = "Stop the Watchtower Raids",
) -> str:
    lines = [
        f"{player_name}    HP: {hp_text}    Gold: {gold}",
        f"Quest: {quest_text}",
        "Layout order: HUD -> map -> scene text -> actions",
    ]
    return _box_panel("HUD", lines)


def build_hud_panel(
    *,
    player_name: str = "Draft Hero",
    hp_text: str = "34/40",
    gold: int = 27,
    quest_text: str = "Stop the Watchtower Raids",
    act_text: str = "Act 1",
) -> Panel:
    table = Table.grid(expand=True)
    table.add_column(ratio=3)
    table.add_column(ratio=2, justify="center")
    table.add_column(ratio=2, justify="right")
    table.add_row(
        Text(player_name, style="bold white"),
        Text(f"HP {hp_text}", style="bold red"),
        Text(f"Gold {gold}", style="bold yellow"),
    )
    table.add_row(
        Text(f"Quest: {quest_text}", style="cyan"),
        Text("Mode: Hybrid Draft", style="magenta"),
        Text(act_text, style="green"),
    )
    return Panel(table, title="HUD", border_style="cyan", box=box.ROUNDED, padding=(0, 1))


def build_overworld_panel_text(blueprint: HybridMapBlueprint, state: DraftMapState) -> str:
    map_lines = _overworld_card_lines(blueprint, state)
    sidebar_lines = _overworld_sidebar_lines(blueprint, state)
    lines = _combine_overworld_map_and_sidebar(map_lines, sidebar_lines)
    return _box_panel("Overworld Route Map", lines, width=96)


def build_overworld_panel(blueprint: HybridMapBlueprint, state: DraftMapState) -> Panel:
    map_content = Align.center(Group(*_overworld_card_lines_rich(blueprint, state)))

    route_key = Text.assemble(
        ("( NAME ) ", "bold black on bright_cyan"),
        ("Current\n", "white"),
        ("[ NAME ] ", "bold green"),
        ("Explored\n", "white"),
        ("[ ????? ] ", "dim"),
        ("Hidden", "white"),
    )
    travel = Text("\n".join(_overworld_travel_lines(blueprint, state)), style="green")
    location = Text("\n".join(_overworld_location_lines(blueprint, state)), style="white")
    sidebar = Group(
        Panel(route_key, title="Route Key", border_style="cyan", box=box.SIMPLE),
        Panel(travel, title="Travel", border_style="green", box=box.SIMPLE),
        Panel(location, title="Location", border_style="magenta", box=box.SIMPLE),
    )

    layout = Table.grid(expand=True, padding=(0, 2))
    layout.add_column(ratio=5)
    layout.add_column(width=_OVERWORLD_SIDEBAR_WIDTH + 4)
    layout.add_row(map_content, sidebar)
    return Panel(layout, title="Overworld Route Map", border_style="green", box=box.ROUNDED, padding=(0, 1))


def _room_symbol(dungeon: DungeonMap, room_id: str, state: DraftMapState) -> str:
    room = dungeon.rooms[room_id]
    if state.current_room_id == room_id:
        return "P"
    if room_id in state.cleared_rooms:
        return "."
    if requirement_met(state, room.requirement):
        return ROLE_SYMBOLS.get(room.role, "?")
    return "?"


def _rich_room_symbol(dungeon: DungeonMap, room_id: str, state: DraftMapState) -> Text:
    room = dungeon.rooms[room_id]
    if state.current_room_id == room_id:
        return Text(" P ", style="bold black on bright_cyan")
    if room_id in state.cleared_rooms:
        return Text(" . ", style="green")
    if requirement_met(state, room.requirement):
        symbol = ROLE_SYMBOLS.get(room.role, "?")
        style_by_role = {
            "entrance": "bold cyan",
            "combat": "bold red",
            "event": "bold yellow",
            "treasure": "bold yellow",
            "boss": "bold magenta",
            "exit": "bold green",
        }
        return Text(f" {symbol} ", style=style_by_role.get(room.role, "white"))
    return Text(" ? ", style="dim")


def _room_anchor(room) -> tuple[int, int]:
    return (room.x * 2, room.y * 2)


def _visible_room(room_id: str, dungeon: DungeonMap, state: DraftMapState) -> bool:
    room = dungeon.rooms[room_id]
    return room_id == (state.current_room_id or dungeon.entrance_room_id) or room_id in state.cleared_rooms or requirement_met(state, room.requirement)


def _corridor_connections(dungeon: DungeonMap, state: DraftMapState) -> dict[tuple[int, int], set[str]]:
    connections: dict[tuple[int, int], set[str]] = {}
    for room in dungeon.rooms.values():
        if not _visible_room(room.room_id, dungeon, state):
            continue
        for target_id in room.exits:
            if not _visible_room(target_id, dungeon, state):
                continue
            target = dungeon.rooms[target_id]
            path = room_travel_path(dungeon, room, target)
            if not path:
                continue
            points = [_room_anchor(room), *path]
            for index in range(1, len(points) - 1):
                prev_x, prev_y = points[index - 1]
                current = points[index]
                next_x, next_y = points[index + 1]
                curr_x, curr_y = current
                cell_connections = connections.setdefault(current, set())
                if prev_x < curr_x:
                    cell_connections.add("L")
                elif prev_x > curr_x:
                    cell_connections.add("R")
                elif prev_y < curr_y:
                    cell_connections.add("U")
                elif prev_y > curr_y:
                    cell_connections.add("D")
                if next_x < curr_x:
                    cell_connections.add("L")
                elif next_x > curr_x:
                    cell_connections.add("R")
                elif next_y < curr_y:
                    cell_connections.add("U")
                elif next_y > curr_y:
                    cell_connections.add("D")
    return connections


def _corridor_glyph(directions: set[str]) -> str:
    if not directions:
        return "   "
    if directions.issubset({"L", "R"}):
        return "---"
    if directions.issubset({"U", "D"}):
        return " | "
    return " + "


def _rich_corridor_glyph(directions: set[str]) -> Text:
    glyph = _corridor_glyph(directions)
    if not directions:
        return Text(glyph)
    if directions.issubset({"L", "R"}):
        return Text(glyph, style="cyan")
    if directions.issubset({"U", "D"}):
        return Text(glyph, style="cyan")
    return Text(glyph, style="bold cyan")


def _compass_lines() -> list[str]:
    return [
        "   NORTH",
        "     |",
        "WEST-+-EAST",
        "     |",
        "   SOUTH",
    ]


def _compass_text() -> Text:
    return Text("\n".join(_compass_lines()), style="bold cyan", no_wrap=True, overflow="crop")


def _compass_renderable():
    compass = Table.grid(expand=True, padding=0)
    compass.add_column(ratio=1)
    compass.add_column(width=max(len(line) for line in _compass_lines()), justify="left", no_wrap=True)
    compass.add_row("", _compass_text())
    return compass


def _dungeon_grid_lines(grid: list[list[str]]) -> list[str]:
    border = "+" + "-" * (len(grid[0]) * 3) + "+"
    lines = [border]
    for row in grid:
        lines.append("|" + "".join(f" {cell} " if len(cell) == 1 else cell for cell in row) + "|")
    lines.append(border)
    return lines


def _dungeon_grid_with_compass_lines(grid: list[list[str]], *, content_width: int = 74) -> list[str]:
    map_lines = _dungeon_grid_lines(grid)
    compass_lines = _compass_lines()
    map_width = max(len(line) for line in map_lines)
    compass_width = max(len(line) for line in compass_lines)
    right_padding = 2
    compass_gap = 2
    content_width = max(content_width, map_width + 2 * (compass_width + right_padding + compass_gap))
    map_x = max(0, (content_width - map_width) // 2)
    compass_x = max(0, content_width - compass_width - right_padding)
    layer_height = max(len(map_lines), len(compass_lines))
    canvas = [list(" " * content_width) for _ in range(layer_height)]

    for y, map_line in enumerate(map_lines):
        for x, char in enumerate(map_line):
            canvas[y][map_x + x] = char

    for y, compass_line in enumerate(compass_lines):
        for x, char in enumerate(compass_line):
            canvas[y][compass_x + x] = char

    return ["".join(line).rstrip() for line in canvas]


def _dungeon_render_rows(dungeon: DungeonMap, state: DraftMapState) -> list[list[str]]:
    fine_width = max(1, dungeon.width * 2 - 1)
    fine_height = max(1, dungeon.height * 2 - 1)
    room_lookup = {_room_anchor(room): room for room in dungeon.rooms.values()}
    corridor_lookup = _corridor_connections(dungeon, state)
    rows: list[list[str]] = []
    for y in range(fine_height):
        row: list[str] = []
        for x in range(fine_width):
            room = room_lookup.get((x, y))
            if room is not None:
                row.append(_room_symbol(dungeon, room.room_id, state))
            else:
                row.append(_corridor_glyph(corridor_lookup.get((x, y), set())))
        rows.append(row)
    return rows


def _dungeon_render_rows_rich(dungeon: DungeonMap, state: DraftMapState) -> list[list[Text]]:
    fine_width = max(1, dungeon.width * 2 - 1)
    fine_height = max(1, dungeon.height * 2 - 1)
    room_lookup = {_room_anchor(room): room for room in dungeon.rooms.values()}
    corridor_lookup = _corridor_connections(dungeon, state)
    rows: list[list[Text]] = []
    for y in range(fine_height):
        row: list[Text] = []
        for x in range(fine_width):
            room = room_lookup.get((x, y))
            if room is not None:
                row.append(_rich_room_symbol(dungeon, room.room_id, state))
            else:
                row.append(_rich_corridor_glyph(corridor_lookup.get((x, y), set())))
        rows.append(row)
    return rows


def build_dungeon_panel_text(dungeon: DungeonMap, state: DraftMapState) -> str:
    grid = _dungeon_render_rows(dungeon, state)
    room = dungeon.rooms[state.current_room_id or dungeon.entrance_room_id]
    move_lines = _directional_exit_lines(dungeon, state)
    legend_line = "Legend: P you, . cleared, E combat, * event, T treasure, B boss, ? locked, corridors show open routes"
    content_width = max(
        74,
        len(dungeon.title) + 2,
        len(f"Current room: {room.title}"),
        len("Available moves:"),
        len(legend_line),
        *(len(line) for line in move_lines),
    )
    lines: list[str] = []
    lines.extend(_dungeon_grid_with_compass_lines(grid, content_width=content_width))
    lines.append("")
    lines.append(f"Current room: {room.title}")
    lines.append("Available moves:")
    lines.extend(move_lines)
    lines.append("")
    lines.append(legend_line)
    return _box_panel(dungeon.title, lines, width=78)


def build_dungeon_panel(dungeon: DungeonMap, state: DraftMapState) -> Panel:
    grid = Table.grid(padding=0)
    rendered_rows = _dungeon_render_rows_rich(dungeon, state)
    for _ in range(len(rendered_rows[0])):
        grid.add_column(justify="center", width=3)

    for row in rendered_rows:
        grid.add_row(*row)

    room = dungeon.rooms[state.current_room_id or dungeon.entrance_room_id]
    info = Table.grid(expand=True, padding=(0, 1))
    info.add_column(ratio=2)
    info.add_column(ratio=3)
    info.add_row(Text("Current Room", style="bold cyan"), Text(room.title, style="bold white"))
    info.add_row(Text("Role", style="cyan"), Text(room.role.upper(), style="magenta"))
    info.add_row(Text("Summary", style="cyan"), Text(room.summary, style="white"))
    info.add_row(
        Text("Available Moves", style="cyan"),
        Text(_directional_exit_text(dungeon, state), style="green" if current_room_exits(dungeon, state) else "dim"),
    )

    legend = Table.grid(expand=True)
    legend.add_column(justify="center")
    legend.add_column(justify="center")
    legend.add_column(justify="center")
    legend.add_row(
        Text("P player", style="bold black on bright_cyan"),
        Text(". cleared  E fight  * event  T treasure", style="bold yellow"),
        Text("B boss  ? locked  corridors mark open routes", style="bold magenta"),
    )

    map_header = Table.grid(expand=True, padding=0)
    map_header.add_column(ratio=1)
    map_header.add_column(justify="center", width=len(rendered_rows[0]) * 3)
    map_header.add_column(ratio=1)
    map_header.add_row("", grid, _compass_renderable())

    group = Group(map_header, info, legend)
    return Panel(group, title=dungeon.title, border_style="magenta", box=box.ROUNDED, padding=(0, 1))


def build_screen_text(
    *,
    blueprint: HybridMapBlueprint,
    state: DraftMapState,
    dungeon: DungeonMap | None = None,
    player_name: str = "Draft Hero",
    hp_text: str = "34/40",
    gold: int = 27,
    quest_text: str = "Stop the Watchtower Raids",
    scene_text: str = "A draft presentation pass using a rich-guided panel layout.",
) -> str:
    sections = [
        build_hud_panel_text(player_name=player_name, hp_text=hp_text, gold=gold, quest_text=quest_text),
        build_overworld_panel_text(blueprint, state),
    ]
    if dungeon is not None:
        sections.append(build_dungeon_panel_text(dungeon, state))
    sections.append(_box_panel("Scene", [scene_text, "Actions would render below the active map panel."]))
    return "\n\n".join(sections)


def build_scene_panel(scene_text: str) -> Panel:
    table = Table.grid(expand=True)
    table.add_column()
    table.add_row(Text(scene_text, style="white"))
    table.add_row(Text("Actions would render below the active map panel.", style="dim"))
    return Panel(table, title="Scene", border_style="yellow", box=box.ROUNDED, padding=(0, 1))


def render_screen_with_rich(
    *,
    blueprint: HybridMapBlueprint,
    state: DraftMapState,
    dungeon: DungeonMap | None = None,
    player_name: str = "Draft Hero",
    hp_text: str = "34/40",
    gold: int = 27,
    quest_text: str = "Stop the Watchtower Raids",
    act_text: str = "Act 1",
    scene_text: str = "A draft presentation pass using a rich-guided panel layout.",
    console: Console | None = None,
) -> str:
    if not RICH_AVAILABLE:
        return build_screen_text(
            blueprint=blueprint,
            state=state,
            dungeon=dungeon,
            player_name=player_name,
            hp_text=hp_text,
            gold=gold,
            quest_text=quest_text,
            scene_text=scene_text,
        )

    active_console = console or Console()

    hud = build_hud_panel(
        player_name=player_name,
        hp_text=hp_text,
        gold=gold,
        quest_text=quest_text,
        act_text=act_text,
    )

    if dungeon is None:
        body = build_overworld_panel(blueprint, state)
    else:
        if active_console.width >= 140:
            body = Table.grid(expand=True)
            body.add_column(ratio=5)
            body.add_column(ratio=4)
            body.add_row(
                build_overworld_panel(blueprint, state),
                build_dungeon_panel(dungeon, state),
            )
        else:
            body = Group(
                build_overworld_panel(blueprint, state),
                build_dungeon_panel(dungeon, state),
            )

    active_console.print(Group(hud, body, build_scene_panel(scene_text)))
    return ""
