# orun19 F1: the first films

Verified against source: 2026-10-23. Charter F1, first part. These films are
made while S2a trains. They live outside the repository: `~/orun19-films/`
for policy films and `~/mocap/films/` for anything drawn from capture data
(D5/D5a). For the run's page, which the scribe keeps.

| film | what it shows | sha256 | length |
|---|---|---|---|
| `~/orun19-films/v06-standing.webm` | leo v06 standing, one full turn, 12° above the floor, 480 px | `82e05f42` | 6.0 s, 150 frames |
| `~/orun19-films/s1-v06-vs-b1-s2.webm` | s1-v06-180 (v06) beside b1-s2-180 (v05) at 0.7 and 3.5 m/s commanded, seed 1001, 6–8 s, real time then 1/2 | `16244dd6` | 12.0 s, 300 frames |
| `~/mocap/films/m1-cheetah-v06.webm` | M1's clips cheetah52/59/61 against the AcinoSet cheetah, 3 loops then 1/4 | `25e230a7` | 8.4 s, 506 frames |
| `~/mocap/films/m2-dog-v06.webm` | M2's clips gallop27/34/42 (carpus target) against the AI4Animation dog, 3 loops then 1/4 | `103700da` | 9.4 s, 566 frames |

Every film passed its decode check: every encoded frame decodes.

- **Standing** is frame 0 (t = 0) of seed 1001's trace in `s1-v06-180-700`
  (trace `f64761fa`, model `f9b8ab82`). That is the standing keyframe as the
  evaluation spawned it, before the first action. The lowest bound is
  4.3 mm over the collision plane.
- **S beside v05** shows the two commands where s1-v06-180 tracks (O3). The
  panels are s1-v06-180 (policy `bd32a42c`, model `f9b8ab82`) and b1-s2-180
  (policy `8adbb84f`, model `59bc5407`), with one scale per clip. Chest
  speed in the 2 s window on seed 1001:

  | command | v06 s1-v06-180 | v05 b1-s2-180 |
  |---|---|---|
  | 0.7 m/s | 0.776 m/s | 1.882 m/s |
  | 3.5 m/s | 3.759 m/s | 1.755 m/s |

  These are window speeds for the film only. The judged tables are in
  `s1-v06-180.md` and `orun18/b1-s2-180.md`.
- **The retarget films** draw the clip the bundle trains on.
  `retarget_film.py` (this folder) solves each stride the way
  `acino_retarget.py` / `dog_retarget.py` did, carpus target and tail mapped,
  and stops unless the solved clip's sha256 equals the stored clip's. All six
  matched: cheetah52 `8ccbe89c`, cheetah59 `aa81d5ad`, cheetah61 `81035ca2`,
  gallop27 `ee0ec468`, gallop34 `a5cf10d7`, gallop42 `a5dee19c`. The drawing
  is orun18's, unchanged, except that it is relabelled v06 and the dot marks
  a ball that is down. It is a drawing, not a measurement. The misses are in
  `m1-retarget.md` and `m2-retarget.md`.

Not yet filmed (F1's remainder): v06 at every tracked speed of an S2 policy
that tracks, M1 and M2 trained policies beside S, and L1.

## Reproduce

```
P=~/cadex-projects/leo; E=$P/evaluations
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun19/stand_film.py $P $E/s1-v06-180-700 \
  ~/orun19-films/v06-standing.webm
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/side_film.py $P ~/orun19-films/s1-v06-vs-b1-s2.webm \
  'cmd 0.7 m/s@s1-v06-180-700=v06 s1-v06-180,b1-s2-180-700=v05 b1-s2-180' \
  'cmd 3.5 m/s@s1-v06-180-3500=v06 s1-v06-180,b1-s2-180-3500=v05 b1-s2-180'
A=~/mocap/acinoset; O=$A/retargeted-v06; X=~/mocap/ai4animation/extract; D=~/mocap/retargeted-v06/carpus
M=$P/runs/s1-v06/train/cat_model-model.xml   # f9b8ab82
pixi run python -I docs/probes/orun19/retarget_film.py $M ~/mocap/films/m1-cheetah-v06.webm 26 3 4 \
  $A/2017_12_12/top/cetane/run1_2/fte_pw/fte.pickle:146:188:cheetah52:$O/cheetah52.clip.json \
  $A/2017_12_12/top/cetane/run1_2/fte_pw/fte.pickle:104:144:cheetah59:$O/cheetah59.clip.json \
  $A/2017_09_03/bottom/zorro/run2_1/fte_pw/fte.pickle:30:71:cheetah61:$O/cheetah61.clip.json
pixi run python -I docs/probes/orun19/retarget_film.py $M ~/mocap/films/m2-dog-v06.webm 26 3 4 \
  $X/D1_010_KAN01_001.bvh:404:432:gallop27:$D/gallop27.clip.json:carpus \
  $X/D1_010_KAN01_003.bvh:86:112:gallop34:$D/gallop34.clip.json:carpus \
  $X/D1_010_KAN01_002.bvh:66:92:gallop42:$D/gallop42.clip.json:carpus
```

The side film takes about 10 minutes on the CPU. The other three take a few
minutes each.
