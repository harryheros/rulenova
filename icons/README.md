# RuleNova icons

16 original icons in two styles, for policy groups and other places where a network client shows a custom icon.

**Solid** — on a rounded colour tile

![Solid icons](preview-solid.png)

**Transparent** — no background

![Transparent icons](preview-transparent.png)

## Usage

Both styles use the same file names, so switching style only changes the folder in the URL:

```text
https://cdn.jsdelivr.net/gh/harryheros/rulenova@main/icons/solid/<name>.png
https://cdn.jsdelivr.net/gh/harryheros/rulenova@main/icons/transparent/<name>.png
```

Example for a Quantumult X policy group:

```ini
static=Streaming, proxy, direct, img-url=https://cdn.jsdelivr.net/gh/harryheros/rulenova@main/icons/solid/blue-compass.png
```

Other clients that support custom policy-group icons use the same URLs in their own icon field. The files are served through jsDelivr, which is reachable in many networks where raw.githubusercontent.com is blocked or slow.

## All icons

| Solid | Transparent | Name |
|:-----:|:-----------:|------|
| <img src="solid/amber-sun.png" width="48" alt="amber-sun solid"> | <img src="transparent/amber-sun.png" width="48" alt="amber-sun transparent"> | `amber-sun` |
| <img src="solid/blue-compass.png" width="48" alt="blue-compass solid"> | <img src="transparent/blue-compass.png" width="48" alt="blue-compass transparent"> | `blue-compass` |
| <img src="solid/coral-flame.png" width="48" alt="coral-flame solid"> | <img src="transparent/coral-flame.png" width="48" alt="coral-flame transparent"> | `coral-flame` |
| <img src="solid/cyan-wave.png" width="48" alt="cyan-wave solid"> | <img src="transparent/cyan-wave.png" width="48" alt="cyan-wave transparent"> | `cyan-wave` |
| <img src="solid/emerald-lotus.png" width="48" alt="emerald-lotus solid"> | <img src="transparent/emerald-lotus.png" width="48" alt="emerald-lotus transparent"> | `emerald-lotus` |
| <img src="solid/golden-orbit.png" width="48" alt="golden-orbit solid"> | <img src="transparent/golden-orbit.png" width="48" alt="golden-orbit transparent"> | `golden-orbit` |
| <img src="solid/ice-mountains.png" width="48" alt="ice-mountains solid"> | <img src="transparent/ice-mountains.png" width="48" alt="ice-mountains transparent"> | `ice-mountains` |
| <img src="solid/indigo-spiral.png" width="48" alt="indigo-spiral solid"> | <img src="transparent/indigo-spiral.png" width="48" alt="indigo-spiral transparent"> | `indigo-spiral` |
| <img src="solid/lavender-infinity.png" width="48" alt="lavender-infinity solid"> | <img src="transparent/lavender-infinity.png" width="48" alt="lavender-infinity transparent"> | `lavender-infinity` |
| <img src="solid/lime-circuit.png" width="48" alt="lime-circuit solid"> | <img src="transparent/lime-circuit.png" width="48" alt="lime-circuit transparent"> | `lime-circuit` |
| <img src="solid/magenta-knot.png" width="48" alt="magenta-knot solid"> | <img src="transparent/magenta-knot.png" width="48" alt="magenta-knot transparent"> | `magenta-knot` |
| <img src="solid/mint-network.png" width="48" alt="mint-network solid"> | <img src="transparent/mint-network.png" width="48" alt="mint-network transparent"> | `mint-network` |
| <img src="solid/rose-crystal.png" width="48" alt="rose-crystal solid"> | <img src="transparent/rose-crystal.png" width="48" alt="rose-crystal transparent"> | `rose-crystal` |
| <img src="solid/sapphire-eye.png" width="48" alt="sapphire-eye solid"> | <img src="transparent/sapphire-eye.png" width="48" alt="sapphire-eye transparent"> | `sapphire-eye` |
| <img src="solid/teal-shield.png" width="48" alt="teal-shield solid"> | <img src="transparent/teal-shield.png" width="48" alt="teal-shield transparent"> | `teal-shield` |
| <img src="solid/violet-links.png" width="48" alt="violet-links solid"> | <img src="transparent/violet-links.png" width="48" alt="violet-links transparent"> | `violet-links` |

## Details

- PNG, 208×208 px, RGBA. Solid icons have transparent rounded corners.
- File names are lowercase; URLs are case-sensitive.
- `sources/scripts/test_icons.py` checks in CI that both styles contain the same icons, every file is a valid 208×208 RGBA PNG, and every icon is listed here.
- After adding or changing icons, regenerate the previews with `python3 sources/scripts/build_icon_preview.py` (requires Pillow).

## License

The icons are original artwork of this project and are covered by the repository license, [CC BY-NC-SA 4.0](../LICENSE): free for non-commercial use with attribution. Commercial use requires prior written permission — see [COMMERCIAL_LICENSE.md](../COMMERCIAL_LICENSE.md).
