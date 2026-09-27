# The Cadex design language — small printed servo robots

Verified against source: 2026-09-27. Provenance: `[Cadex-new]`.

This is how a robot that Cadex designs should look: a small legged or
wheeled machine, 3D-printed around hobby servos (MG90S class), carrying its
own electronics. It is the language the product agent is taught (ot10 A4),
the thing the renderer presents (A2), the thing `look` and review measure
(A3), and what the ot10 rubric scores (`docs/probes/ot10/README.md`).

It was distilled from the owner's core reference set, which is local and
gitignored (`reference/`). Each rule names the references it comes from by
filename only; no reference image is copied, described in a prompt, or
shown to the product agent. The agent learns only what is written here.

**Exists today versus target.** On 2026-09-27 none of this is
product behaviour. The renderer draws flat orthographic tessellation in
one printed colour and one purchased colour (ADR-406, ADR-410). xscript has
no appearance roles, and the overlay teaches six rules of form (fillets,
enclosure, continuous parts, mirroring, proportion, printability) but not
palette, joints, face or presentation. The baseline is hex3, which scores
2 of 21 on the rubric (`docs/probes/ot10/README.md`, *Baseline*). Each rule
below says which ot10 criterion builds it.

## 0. The one-sentence version

**A light shell over a dark mechanism, one accent, every joint a round
feature, one soft body primitive with a face, limbs that taper to distinct
feet, presented in a studio.**

Of the core set, `07-white-hood-quadruped-yellow-studio.jpg` shows the
whole language in one image. The others each show one part of it.

## 1. Form: shell over skeleton

- **The body is one readable primitive**: a hood, a pill, a sphere or a
  heavily rounded box. It is not a deck of plates. (`07-white-hood-quadruped-yellow-studio.jpg`,
  `43-yellow-sphere-quadruped-dark-legs.jpg`, `39-grey-wheel-leg-hexapod-product.jpg`,
  `14-ibots-crab-white-shell-dark-visor.jpg`)
- **Shells hide the purchased hardware.** Servo cases, boards and the
  battery sit inside printed shells shaped around them. What shows of the
  mechanism is deliberate: a dark band, a ring, a joint. It is never an
  exposed case or a bare board. (`07-white-hood-quadruped-yellow-studio.jpg`,
  `14-ibots-crab-white-shell-dark-visor.jpg`, `26-white-frog-shell-dark-joints.jpg`,
  `01-desktop-arm-product-finish.jpg`)
- **Skeleton first, shell second.** The mechanism (servos, horns,
  brackets and links) is designed to fit and move. The shell is a separate
  printed part over it, with a clearance gap, fastened to the skeleton.
  It is never fused into the mechanism, so the gap never becomes a fit
  failure. (`39-grey-wheel-leg-hexapod-product.jpg`, `46-orange-spider-concept-sheet.jpg`)
- **Split lines are the only surface detail.** Where two shell pieces meet,
  the seam is a clean groove or step that follows the form. There are no
  greebles, vents or stuck-on panels. (`39-grey-wheel-leg-hexapod-product.jpg`,
  `01-desktop-arm-product-finish.jpg`, `43-yellow-sphere-quadruped-dark-legs.jpg`)
- **Soft primitives, large radii.** Outside radii are about 10–20% of the
  part's smallest overall dimension: 4–8 mm on a 40 mm body, not a 1 mm
  break. Parts blend into one another at bosses and roots, and are not
  butted together. (`08-grey-cad-render-filleted-joints.jpg`,
  `12-tan-folded-quadruped-chunky.jpg`, `01-desktop-arm-product-finish.jpg`)

## 2. Materials and palette: two materials, one accent

Three **appearance roles**, and every part has exactly one:

| role | what it is | default colour | alternates |
|---|---|---|---|
| `shell` | the printed outer forms: body, hood, limb covers | bone `#E9E6DF` | cool grey `#B9BDC2`, tan `#C9AE86` |
| `mechanism` | joints, links a shell does not cover, face panel, feet, all purchased hardware that shows | graphite `#2F3237` | — |
| `accent` | one saturated colour on a few deliberate features: joint rings, the eye, foot tips | signal orange `#F26A1B` | yellow `#F2B40A`, teal `#179C98` |

- **At most three materials on the whole robot**: one shell colour, the
  graphite mechanism and at most one accent. A robot without an accent is
  fine; a rainbow is not. The accent covers a small share of the surface,
  roughly under 10%. (`07-white-hood-quadruped-yellow-studio.jpg`,
  `04-jerboa-poster-orange-accent.jpg`, `43-yellow-sphere-quadruped-dark-legs.jpg`,
  `26-white-frog-shell-dark-joints.jpg`)
- **One material is also a valid language** when the proportions and
  bosses carry the design: a single tan or grey. In that case the joints
  and face are made by geometry, not by colour. (`12-tan-folded-quadruped-chunky.jpg`,
  `08-grey-cad-render-filleted-joints.jpg`, `39-grey-wheel-leg-hexapod-product.jpg`)
- **Colour follows role, not supplier.** Being purchased is not a colour.
  A servo that shows is `mechanism` because it is mechanism. hex3's
  printed-orange / purchased-grey split is the thing this replaces.
- **The body can take the accent instead.** When the shell itself is
  saturated (yellow, orange), the mechanism stays graphite and there is no
  third colour. (`43-yellow-sphere-quadruped-dark-legs.jpg`,
  `46-orange-spider-concept-sheet.jpg`)

xscript declares the role per part and the palette per assembly
(`assembly.component(..., appearance=)`, `assembly.assembly(..., palette=)`,
`docs/XSCRIPT.md`, ADR-413), and inventory, `render`, `look` and review
carry them. An undeclared part is drawn by supplier until it declares one.

## 3. Joints are features

- **Every rotation axis is a round feature**: a boss, ring or cap
  concentric with the axis, at least as wide as the servo horn it covers.
  The joint is not hidden and it is not a bare horn.
  (`26-white-frog-shell-dark-joints.jpg`, `12-tan-folded-quadruped-chunky.jpg`,
  `08-grey-cad-render-filleted-joints.jpg`, `01-desktop-arm-product-finish.jpg`)
- **The servo horn becomes a disc.** A printed cap covers the horn and its
  screw. It reads as a hub, not as an arm. (`04-jerboa-poster-orange-accent.jpg`)
- **All joints look the same.** One cap design and one diameter step
  serve the whole robot. (`46-orange-spider-concept-sheet.jpg`,
  `26-white-frog-shell-dark-joints.jpg`)
- **The Cadex joint cap** is the proposed signature: a graphite disc cap
  on every actuated axis, carrying a thin accent ring around its rim. It
  holds across body plans because every Cadex robot has servos. It is
  the orange ring of `04-jerboa-poster-orange-accent.jpg` and the dark
  joint ring of `26-white-frog-shell-dark-joints.jpg`, made into one rule.

## 4. A face

- **One focal element on the forward face** turns a mechanism into a
  character. It can be a dark visor slot, a lens cluster, one or two
  round eyes, or a dark face panel. It sits in `mechanism` graphite and
  may carry the accent. (`07-white-hood-quadruped-yellow-studio.jpg`,
  `14-ibots-crab-white-shell-dark-visor.jpg`, `43-yellow-sphere-quadruped-dark-legs.jpg`,
  `26-white-frog-shell-dark-joints.jpg`)
- **The face defines the front.** It sits on the body's forward axis, the
  same +X the IMU is mounted along, so the face is where the robot walks.
- **The face can be functional.** A recess for a sensor, or the window
  over the controller's LED, is better than an ornament.
  (`43-yellow-sphere-quadruped-dark-legs.jpg`)
- **It is a proportion, not a sticker.** The face occupies about 25–50%
  of the body's front face and is recessed into the shell or split from
  it. It is not a thin plate on the surface. (`07-white-hood-quadruped-yellow-studio.jpg`,
  `14-ibots-crab-white-shell-dark-visor.jpg`)

## 5. Proportion and taper

- **A compact body.** Mass is gathered into one volume, with the battery
  low and central (the overlay's existing rule). A flat, sprawling deck is
  what hex3 was. (`43-yellow-sphere-quadruped-dark-legs.jpg`, `12-tan-folded-quadruped-chunky.jpg`,
  `07-white-hood-quadruped-yellow-studio.jpg`)
- **Limbs taper towards the foot.** Near the foot, a limb's section is
  clearly smaller than at the hip: about 60% or less. It is not a
  constant bar. (`07-white-hood-quadruped-yellow-studio.jpg`,
  `14-ibots-crab-white-shell-dark-visor.jpg`, `46-orange-spider-concept-sheet.jpg`)
- **Feet are distinct.** Each foot is a cap, pad, point or wheel, in
  `mechanism` or `accent`. It is not the end of a bar. (`07-white-hood-quadruped-yellow-studio.jpg`,
  `39-grey-wheel-leg-hexapod-product.jpg`, `26-white-frog-shell-dark-joints.jpg`)
- **Segmented legs read as a rhythm.** Repeated segments alternate shell
  and mechanism: a light cover, a dark joint, a light cover.
  (`46-orange-spider-concept-sheet.jpg`, `14-ibots-crab-white-shell-dark-visor.jpg`)

## 6. Printability

The overlay's existing rules stay: a flat face to print on, no overhang
past 45°, walls of at least 1.6 mm, holes sized to their fastener. The
language adds:

- **Shells print as shells**: 1.6–2.4 mm walls, opening downwards, with
  the rim as the print face. A hood is one print. (`07-white-hood-quadruped-yellow-studio.jpg`,
  `43-yellow-sphere-quadruped-dark-legs.jpg`)
- **Split where the printer needs a face.** A form too round to print in
  one piece is split along a line that is also the design's split line
  (§1). (`39-grey-wheel-leg-hexapod-product.jpg`, `01-desktop-arm-product-finish.jpg`)
- **Colour is a part boundary.** Each role is a separate printed part,
  printed in its own filament. There is no painting and no multi-material
  print. The accent ring of a joint cap is its own small part.
  (`12-tan-folded-quadruped-chunky.jpg` shows that one material also prints.)
- **Fasteners are hidden or deliberate.** Screws go in from inside the
  shell or under a cap. Where they show, they are an even pattern.
  (`01-desktop-arm-product-finish.jpg`)

## 7. Presentation

A design is judged the way it is shown. (`07-white-hood-quadruped-yellow-studio.jpg`,
`04-jerboa-poster-orange-accent.jpg`, `46-orange-spider-concept-sheet.jpg`,
`08-grey-cad-render-filleted-joints.jpg`)

- **The hero shot** is taken from a low three-quarter view: the camera
  15–25° above the floor, 30–45° off the front, looking at the face.
- **Studio light, so that curvature reads.** A key light, a soft fill and
  a rim light give smooth shading across large radii. Flat shading, which
  is what `look` drew before ADR-412, hides the only thing radii are for.
- **A seamless backdrop**: light grey, or one saturated colour taken from
  the accent. There is no horizon line and no grid.
- **A soft contact shadow** under the robot, so it stands on something.
- **Antialiased edges.**
- **A concept sheet** presents a design: the hero, orthographic line
  views, the palette swatches, the name and the key numbers (mass, servo
  count, size). (`46-orange-spider-concept-sheet.jpg`, `04-jerboa-poster-orange-accent.jpg`)

Built by ot10 A2 (hero render: `render`'s `hero.png` and `look`'s `hero` view, ADR-412) and A6 (concept sheet).

## 8. The order of design

The language is applied in this order, which is the order the product
agent is taught (A4):

1. **Concept**: name the silhouette, the character (what the face is),
   the palette (shell colour and accent) and the body primitive before
   any geometry.
2. **Skeleton**: the mechanism, electronics and fit, as the overlay
   already teaches. This is where the fit checks pass.
3. **Shell**: the body primitive, limb covers, joint caps, face and feet,
   each with a role, clear of the skeleton.
4. **Refine with `look`**: judge the render against §1–§6, fix the worst
   thing, and look again.

## 9. What this is not

- **Not a copy.** No reference is reproduced. §3's joint cap is where
  Cadex's own signature starts. The long-term rung of ot10 is making it
  hold across body plans.
- **Not ornament over function.** A shell never changes the joint axes,
  the mass budget beyond its own weight, or the fit. A design that looks
  right and fails its fit checks is not accepted.
- **Not a mood board.** The tier-2 and tier-3 references are not cited
  here. Where they disagree with the core set, the core set wins.
