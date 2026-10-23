# orun14: leo's clearance baseline at 4c9de98d, pair by pair

Verified against source: 2026-10-21. The build p1-flat trains on (project
git `18afa79`; reports committed at `77a02d8`, static, and `825ddec`,
sweep). A later model change (O1) is compared against this list with
`docs/probes/orun13/clearance_diff.py BEFORE_DIR AFTER_DIR`, each DIR holding
that build's `docs/clearance.md` and `docs/clearance-sweep.md`. It may add no
pair.

## Static: 14 failing pairs of 8,911 (`cadex clearance`, initial pose)

| first | second | distance mm | common volume mm³ | verdict | note |
|---|---|---|---|---|---|
| c_meta_hl | c_heel_hl | 0.0 | 168.2 | intersection | welded by `w_heel_hl` |
| c_meta_hr | c_heel_hr | 0.0 | 154.2 | intersection | welded by `w_heel_hr` |
| c_crank_fl | c_rod_fl | 0.0 | 0 | below clearance | push-rod joint |
| c_paw_fl | c_rod_fl | 0.0 | 0 | below clearance | push-rod joint |
| c_crank_fr | c_rod_fr | 0.0 | 0 | below clearance | push-rod joint |
| c_paw_fr | c_rod_fr | 0.0 | 0 | below clearance | push-rod joint |
| c_crank_hl | c_rod_hl | 0.0 | 0 | below clearance | push-rod joint |
| c_meta_hl | c_rod_hl | 0.0 | 0 | below clearance | push-rod joint |
| c_crank_hr | c_rod_hr | 0.0 | 0 | below clearance | push-rod joint |
| c_meta_hr | c_rod_hr | 0.0 | 0 | below clearance | push-rod joint |
| c_qdd_elbow_l | c_forearm_l | 2.92 | 0 | missed contact | declared contact |
| c_qdd_elbow_r | c_forearm_r | 2.92 | 0 | missed contact | declared contact |
| c_qdd_knee_l | c_shin_l | 9.48 | 0 | missed contact | declared contact |
| c_qdd_knee_r | c_shin_r | 9.48 | 0 | missed contact | declared contact |

## Swept: 12 failing rows, 8 distinct pairs (`cadex clearance --sweep`, complete, 10° steps)

| joint | first | second | max common volume mm³ |
|---|---|---|---|
| j_shoulder_l | c_chest_frame | c_qdd_wrist_l | 11,270.0 |
| j_shoulder_r | c_chest_frame | c_qdd_wrist_r | 11,247.1 |
| j_shoulder_l / _r | c_chest_frame | c_crank_fl / _fr | 1,091.7 |
| j_shoulder_l / _r | c_chest_frame | c_forearm_l / _r | 1,026.6 |
| j_scap_l / _r | c_chest_frame | c_qdd_wrist_l / _r | 977.1 |
| j_scap_l / _r | c_chest_frame | c_forearm_l / _r | 834.6 |
| j_shoulder_l / _r | c_chest_frame | c_rod_fl / _fr | 289.6 |

Every row is a front-leg part against the chest. `clearance_diff.py` keys
pairs without the joint, so it counts 8 (the forearm and wrist drive pairs
fail through both the shoulder and the scapula).
