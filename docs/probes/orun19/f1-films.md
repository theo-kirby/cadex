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
| `~/mocap/films/m1-cheetah-150-vs-clip.webm` | m1-cheetah-150 beside the clip it trained on, at the slowest (cheetah52, 4.63 m/s) and fastest (cheetah61, 5.33 m/s) stride's command, seed 1001, 6–8 s, real time then 1/2 | `97d59ade` | 12.0 s, 300 frames |
| `~/mocap/films/m2-dog-v06.webm` | M2's clips gallop27/34/42 (carpus target) against the AI4Animation dog, 3 loops then 1/4 | `103700da` | 9.4 s, 566 frames |
| `~/mocap/films/m2-dog-150-vs-clip.webm` | m2-dog-150 beside the clip it trained on, at the slowest (gallop27, 2.76 m/s) and fastest (gallop42, 4.23 m/s) stride's command, seed 1001, 6–8 s, real time then 1/2 | `6e92a939` | 12.0 s, 300 frames |
| `~/orun19-films/s2a-hold-150-tracked.webm` | s2a-hold-150 (S2) at each of its six tracked commands, 0.7, 1.5, 2.4, 3.5, 4.23 and 4.63 m/s, seed 1001, 6–8 s, real time then 1/2 | `bb22f155` | 36.0 s, 900 frames |
| `~/orun19-films/m-vs-s2a.webm` | M2 (m2-dog-150) beside S (s2a-hold-150) at 3.5 and 4.23 m/s, M2's slow and fast shared commands; M1 (m1-cheetah-150) beside S at 4.63 and 5.0 m/s, M1's; seed 1001, 6–8 s, real time then 1/2 | `14dd6ece` | 24.0 s, 600 frames |

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

- **M1 beside its clip** (iteration 16). `clip_side_film.py` (this folder) is
  orun18's `side_film.py`, unchanged, with one more panel: `BUNDLE#K`, stride
  K of the trained bundle's `reference_schedule` (M1's `c3c099af`), its `qpos`
  posed by MuJoCo's kinematics on the bundle's own model (`f9b8ab82`, checked)
  and looped, each loop moved on by the stride's length. Nothing is simulated.
  The loops' equality residual is under 0.001 mm. Both panels share the
  engine's renderer, camera rule, floor and one scale per row. A clip
  is a capture derivative, so the film is under `~/mocap/films/`.

  | row | m1-cheetah-150 (policy `a1b5218a`), chest m/s in the window | clip: speed, stride, period (qpos sha256) |
  |---|---|---|
  | cmd 4.63 m/s | 4.265 (trace `b1650750`) | cheetah52: 4.629 m/s, 1.925 m, 0.416 s (`de2181aa`) |
  | cmd 5.33 m/s | 4.375 (trace `bf54b54e`) | cheetah61: 5.328 m/s, 2.121 m, 0.398 s (`5807de0b`) |

  At 5.33 the policy is 0.95 m/s behind its clip, as judged in
  `m1-cheetah-150.md`.

- **M2 beside its clip** (iteration 17), drawn the same way from M2's bundle
  (`8e9e53fc`, model `f9b8ab82` checked, loop residual 0.0 mm):

  | row | m2-dog-150 (policy `863845a8`), chest m/s in the window | clip: speed, stride, period (qpos sha256) |
  |---|---|---|
  | cmd 2.76 m/s | 3.596 (trace `c03a6592`) | gallop27: 2.756 m/s, 1.317 m, 0.478 s (`89a208b2`) |
  | cmd 4.23 m/s | 4.828 (trace `97e1e271`) | gallop42: 4.233 m/s, 1.842 m, 0.435 s (`f7b2049b`) |

  The policy runs ahead of its clip at both ends, 0.84 and 0.59 m/s on this
  seed, as judged in `m2-dog-150.md`.

- **S2 at its tracked speeds, and M1 and M2 beside S** (iteration 18).
  Drawn by orun18's `side_film.py`, unchanged, from the evaluations' traces.
  The trace drawn is the one each evaluation recorded. s2a-hold-150 had
  been judged only at 0.7–5.0 m/s. It was judged at 4.23 and 4.63 m/s too
  (`s2a-hold-150-top.md`), so that it shares a command with each end of M1
  and M2. M2's commands top out at 4.23 and M1's start at 4.63, so no
  command has all three. Neither film draws a clip, and both are under
  `~/orun19-films/`. Chest speed in the 2 s window on seed 1001:

  | command | s2a-hold-150 (`efe7f96b`) | m2-dog-150 (`863845a8`) | m1-cheetah-150 (`a1b5218a`) |
  |---|---|---|---|
  | 0.7 m/s | 0.848 (trace `18e67647`) | – | – |
  | 1.5 m/s | 1.787 (`69af31f5`) | – | – |
  | 2.4 m/s | 2.947 (`25800604`) | – | – |
  | 3.5 m/s | 4.148 (`133eefa2`) | 4.340 (`630bc6b8`) | – |
  | 4.23 m/s | 4.536 (`e3582001`) | 4.828 (`97e1e271`) | – |
  | 4.63 m/s | 4.584 (`1fcc405b`) | – | 4.265 (`b1650750`) |
  | 5.0 m/s | 4.523 (`450fe949`) | – | 4.366 (`2e2b2df5`) |

  On M2's commands the dog's policy is the faster one, by 0.19–0.29 m/s on
  this seed. On M1's, speed-only S is faster than the cheetah's policy, by
  0.16–0.32 m/s.

Not yet filmed (F1's remainder): L1.

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
R=~/cadex-projects/leo/runs/m1-cheetah/train/mocap_gallop-task.json   # c3c099af
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun19/clip_side_film.py $P ~/mocap/films/m1-cheetah-150-vs-clip.webm \
  "cmd 4.63 m/s@m1-cheetah-150-4630=m1-cheetah-150,$R#0=cheetah52 clip" \
  "cmd 5.33 m/s@m1-cheetah-150-5328=m1-cheetah-150,$R#2=cheetah61 clip"
R=~/cadex-projects/leo/runs/m2-dog/train/mocap_gallop-task.json   # 8e9e53fc
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun19/clip_side_film.py $P ~/mocap/films/m2-dog-150-vs-clip.webm \
  "cmd 2.76 m/s@m2-dog-150-2760=m2-dog-150,$R#0=gallop27 clip" \
  "cmd 4.23 m/s@m2-dog-150-4230=m2-dog-150,$R#2=gallop42 clip"
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/side_film.py $P ~/orun19-films/s2a-hold-150-tracked.webm \
  "cmd 0.7 m/s@$E/s2a-hold-150-700=s2a-hold-150" "cmd 1.5 m/s@$E/s2a-hold-150-1500=s2a-hold-150" \
  "cmd 2.4 m/s@$E/s2a-hold-150-2400=s2a-hold-150" "cmd 3.5 m/s@$E/s2a-hold-150-3500=s2a-hold-150" \
  "cmd 4.23 m/s@$E/s2a-hold-150-4230=s2a-hold-150" "cmd 4.63 m/s@$E/s2a-hold-150-4630=s2a-hold-150"
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/side_film.py $P ~/orun19-films/m-vs-s2a.webm \
  "cmd 3.5 m/s@$E/s2a-hold-150-3500=S s2a-hold-150,$E/m2-dog-150-3500=M2 m2-dog-150" \
  "cmd 4.23 m/s@$E/s2a-hold-150-4230=S s2a-hold-150,$E/m2-dog-150-4230=M2 m2-dog-150" \
  "cmd 4.63 m/s@$E/s2a-hold-150-4630=S s2a-hold-150,$E/m1-cheetah-150-4630=M1 m1-cheetah-150" \
  "cmd 5.0 m/s@$E/s2a-hold-150-5000=S s2a-hold-150,$E/m1-cheetah-150-5000=M1 m1-cheetah-150"
```

The side films take about 10 minutes on the CPU; the last two took about 20
minutes each, run together beside l1-dog's trainer. The other three take a few
minutes each.
