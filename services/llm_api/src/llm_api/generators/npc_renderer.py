"""Render typed NPC models into Jekyll-compatible drafts.

Takes a validated NPC Pydantic model (any of the three types) and produces
a GeneratedDraft with YAML frontmatter and Markdown body suitable for the
existing ``npc`` Jekyll layout.
"""
from __future__ import annotations

from llm_api.models.generated import GeneratedDraft
from llm_api.models.npc_types import (
    CombatNpc,
    PlayerCharacter,
    RoleplayNpc,
)


class StructuredNpcDraft(GeneratedDraft):
    """Jekyll-ready NPC draft produced from structured NPC data."""

    def __init__(
        self,
        *,
        title: str,
        slug: str,
        npc_type: str,
        name: str,
        tags: list[str],
        markdown_body: str,
    ):
        self.title = title
        self.slug = slug
        self.markdown_body = markdown_body
        self._npc_type = npc_type
        self._name = name
        self._tags = tags

    def required_yaml_keys(self) -> list[str]:
        return [
            "layout", "title", "name", "npc_type", "permalink", "category",
            "chapter", "episode", "scene", "jumbo", "thumb", "portrait",
            "tags", "search", "excerpt_separator", "id", "slug",
        ]

    def frontmatter_yaml(self, *, draft_id, campaign: str) -> dict:
        return {
            "layout": "npc",
            "title": self.title,
            "name": self._name,
            "npc_type": self._npc_type,
            "slug": self.slug,
            "id": str(draft_id),
            "permalink": "/npcs/:slug",
            "category": "npc",
            "chapter": "01",
            "episode": "01",
            "scene": "01",
            "jumbo": "",
            "thumb": "/assets/images/placeholders/npc-thumb.png",
            "portrait": "/assets/images/placeholders/npc-portrait.png",
            "tags": self._tags,
            "search": True,
            "excerpt_separator": "",
        }


def render_npc_draft(
    *,
    npc: PlayerCharacter | CombatNpc | RoleplayNpc,
    title: str,
    slug: str,
) -> StructuredNpcDraft:
    """Render any NPC type into a StructuredNpcDraft.

    Args:
        npc: A validated NPC model (PlayerCharacter, CombatNpc, or RoleplayNpc).
        title: Page title for the Jekyll draft.
        slug: URL slug for the draft.

    Returns:
        StructuredNpcDraft ready to be written to the drafts directory.
    """
    match npc:
        case PlayerCharacter():
            body = _render_player_character(npc)
            name = npc.identity.name
            tags = [npc.identity.race, npc.identity.class_, f"Level {npc.identity.level}"]
        case CombatNpc():
            body = _render_combat_npc(npc)
            name = npc.identity.name
            tags = [npc.identity.creature_type, f"CR {npc.challenge.rating}"]
        case RoleplayNpc():
            body = _render_roleplay_npc(npc)
            name = npc.identity.name
            tags = [npc.identity.race, npc.identity.occupation]

    return StructuredNpcDraft(
        title=title,
        slug=slug,
        npc_type=npc.character_type,
        name=name,
        tags=tags,
        markdown_body=body,
    )


# ── Renderers ────────────────────────────────────────────────────────────────


def _render_player_character(pc: PlayerCharacter) -> str:
    """Render a PlayerCharacter to Markdown."""
    lines: list[str] = []
    ident = pc.identity

    lines.append(f"**{ident.name}** — Level {ident.level} {ident.race} {ident.class_}")
    if ident.subclass:
        lines[-1] += f" ({ident.subclass})"
    lines.append(f"**Background:** {ident.background} | **Alignment:** {ident.alignment}")
    lines.append("")

    # Ability scores
    lines.append("## Ability Scores")
    fs = pc.ability_scores.final_scores
    mods = pc.ability_scores.modifiers
    lines.append(
        f"| STR | DEX | CON | INT | WIS | CHA |\n"
        f"|-----|-----|-----|-----|-----|-----|\n"
        f"| {fs.str_} ({mods.str_:+d}) | {fs.dex} ({mods.dex:+d}) "
        f"| {fs.con} ({mods.con:+d}) | {fs.int_} ({mods.int_:+d}) "
        f"| {fs.wis} ({mods.wis:+d}) | {fs.cha} ({mods.cha:+d}) |"
    )
    lines.append("")

    # Combat
    lines.append("## Combat")
    lines.append(f"- **AC:** {pc.combat.armor_class.value} ({pc.combat.armor_class.source})")
    lines.append(f"- **HP:** {pc.combat.hit_points.max}")
    lines.append(f"- **Speed:** {pc.combat.speed}")
    lines.append(f"- **Proficiency Bonus:** +{pc.combat.proficiency_bonus}")
    lines.append("")

    # Features
    if pc.features:
        lines.append("## Features")
        for feat in pc.features:
            lines.append(f"- **{feat.name}** ({feat.source}): {feat.description}")
        lines.append("")

    # Equipment
    if pc.equipment:
        lines.append("## Equipment")
        for item in pc.equipment:
            props = ", ".join(item.properties) if item.properties else ""
            qty = f" x{item.quantity}" if item.quantity > 1 else ""
            lines.append(f"- {item.name}{qty}" + (f" ({props})" if props else ""))
        lines.append("")

    # Spellcasting
    if pc.spellcasting:
        sc = pc.spellcasting
        lines.append("## Spellcasting")
        lines.append(f"**{sc.ability}** — DC {sc.spell_save_dc}, +{sc.spell_attack_bonus} to hit")
        if sc.cantrips:
            lines.append(f"**Cantrips:** {', '.join(sc.cantrips)}")
        if sc.spell_slots:
            slots = ", ".join(f"{k}: {v}" for k, v in sc.spell_slots.items())
            lines.append(f"**Spell Slots:** {slots}")
        for spell in sc.spells_known:
            lines.append(f"- **{spell.name}** (Level {spell.level}): {spell.description}")
        lines.append("")

    # Personality
    lines.append("## Personality")
    for trait in pc.personality.traits:
        lines.append(f"- {trait}")
    if pc.personality.backstory_hook:
        lines.append(f"\n**Backstory:** {pc.personality.backstory_hook}")

    return "\n".join(lines)


def _render_combat_npc(npc: CombatNpc) -> str:
    """Render a CombatNpc to Markdown."""
    lines: list[str] = []
    ident = npc.identity

    lines.append(f"**{ident.name}**")
    lines.append(f"*{ident.creature_type}*")
    lines.append(f"*{ident.role}*")
    lines.append("")
    lines.append(f"**Challenge {npc.challenge.rating}** ({npc.challenge.xp} XP)")
    lines.append("")

    # Combat stats
    lines.append(f"- **AC:** {npc.combat.armor_class.value} ({npc.combat.armor_class.source})")
    lines.append(f"- **HP:** {npc.combat.hit_points.value} ({npc.combat.hit_points.formula})")
    lines.append(f"- **Speed:** {npc.combat.speed}")
    lines.append("")

    # Ability scores
    ab = npc.ability_scores
    lines.append("## Ability Scores")
    lines.append(
        f"| STR | DEX | CON | INT | WIS | CHA |\n"
        f"|-----|-----|-----|-----|-----|-----|\n"
        f"| {ab.str_} | {ab.dex} | {ab.con} | {ab.int_} | {ab.wis} | {ab.cha} |"
    )
    lines.append("")

    # Traits
    if npc.traits:
        lines.append("## Traits")
        for trait in npc.traits:
            lines.append(f"**{trait.name}.** {trait.description}")
            lines.append("")

    # Actions
    lines.append("## Actions")
    for action in npc.actions:
        lines.append(f"**{action.name}.** {action.description}")
        lines.append("")

    # Reactions
    if npc.reactions:
        lines.append("## Reactions")
        for reaction in npc.reactions:
            lines.append(f"**{reaction.name}.** {reaction.description}")
            lines.append("")

    # Tactical notes
    if npc.tactical_notes:
        lines.append("## Tactical Notes")
        lines.append(npc.tactical_notes)

    return "\n".join(lines)


def _render_roleplay_npc(npc: RoleplayNpc) -> str:
    """Render a RoleplayNpc to Markdown."""
    lines: list[str] = []
    ident = npc.identity

    lines.append(f"**{ident.name}** — {ident.race} {ident.occupation}")
    lines.append(f"**Alignment:** {ident.alignment}")
    if ident.age:
        lines.append(f"**Age:** {ident.age}")
    if ident.location:
        lines.append(f"**Location:** {ident.location}")
    lines.append("")

    # Appearance
    if npc.appearance.description:
        lines.append("## Appearance")
        lines.append(npc.appearance.description)
        if npc.appearance.distinguishing_features:
            for feat in npc.appearance.distinguishing_features:
                lines.append(f"- {feat}")
        lines.append("")

    # Personality
    lines.append("## Personality")
    for trait in npc.personality.traits:
        lines.append(f"- {trait}")
    if npc.personality.mannerisms:
        lines.append(f"**Mannerisms:** {npc.personality.mannerisms}")
    if npc.personality.speech_pattern:
        lines.append(f"**Speech:** {npc.personality.speech_pattern}")
    if npc.personality.motivation:
        lines.append(f"**Motivation:** {npc.personality.motivation}")
    lines.append("")

    # Secrets
    if npc.secrets:
        lines.append("## Secrets")
        for secret in npc.secrets:
            lines.append(f"- **{secret.secret}** — Impact: {secret.impact}")
        lines.append("")

    # Relationships
    if npc.relationships:
        lines.append("## Relationships")
        for rel in npc.relationships:
            lines.append(f"- **{rel.name}** ({rel.relationship}) — {rel.attitude}")
        lines.append("")

    # Plot hooks
    if npc.plot_hooks:
        lines.append("## Plot Hooks")
        for hook in npc.plot_hooks:
            lines.append(f"- [{hook.tier.upper()}] {hook.hook}")
        lines.append("")

    return "\n".join(lines)
