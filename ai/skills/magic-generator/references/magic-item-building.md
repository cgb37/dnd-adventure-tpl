# Magic Item Building Reference

Guidance for choosing rarity and budgeting properties once
`scripts/magic_item_rarity.py` confirms what's level-appropriate.

## Rarity by Party Level

| Rarity | Minimum Level | Typically Requires Attunement |
|---|---|---|
| Common | 1 | No |
| Uncommon | 1 | No |
| Rare | 5 | Yes |
| Very Rare | 11 | Yes |
| Legendary | 17 | Yes |

"Typically" means per-item, not universal — a +1 weapon (uncommon) never
requires attunement; a wondrous rare item sometimes doesn't either. Decide
per item, using the script's guidance as the default assumption rather
than an absolute rule.

## Property Budget by Rarity

- **Common**: a single minor, mostly non-combat effect (a self-lighting
  torch, a mess-kit that never needs cleaning). No numeric bonus.
- **Uncommon**: one clear combat or utility benefit — a flat +1 to
  attack/damage/AC/a save, or a single reusable limited-use effect (a
  handful of charges per day).
- **Rare**: a +1 or +2 numeric bonus *plus* one distinct secondary
  property (a triggered effect, a limited-use spell, a passive
  resistance) — not two full-strength benefits stacked freely.
- **Very Rare**: a +2 or +3 numeric bonus plus a meaningful secondary
  property, or two moderate secondary properties without a numeric bonus.
- **Legendary**: a +3 numeric bonus plus a signature, story-relevant
  property that could justify a whole quest arc on its own — this is the
  rarity where the item itself is a plot device, not just gear.

Don't stack two "Rare-tier" properties onto a Common item to make it feel
special — reach for the next rarity tier instead, using the party-level
guidance to confirm it's appropriate.

## Attunement and Limitations

Every item at Rare or above should have at least one of:
- An attunement requirement, optionally restricted to a class/alignment/
  race for a story reason.
- A charge limit or recharge condition (e.g. "3 charges, regains 1d3 at
  dawn").
- A drawback on overuse, a failed save, or a specific trigger (curses,
  backlash damage, an attention-drawing effect).

A magic item with no limitation of any kind is a power-creep risk
regardless of rarity — give the DM a lever to pull if the item turns out
to be too strong at the table.
