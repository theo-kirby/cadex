# SPDX-License-Identifier: LGPL-2.1-or-later

"""Native additive/subtractive loft implementation."""

from __future__ import annotations

from typing import Any

from CadexTransactions import run_freecad_transaction

from . import domain_runtime


def run(
    service: Any,
    *,
    operation: str,
    type_id: str,
    profile_names: list[str],
    label: str,
    closed: bool,
    ruled: bool,
    reversed: bool,
    midplane: bool,
    refine: bool,
) -> dict[str, Any]:
    clean_label = str(label or "").strip()
    if not clean_label:
        return _invalid("label is required.")
    if not isinstance(profile_names, list) or len(profile_names) < 2:
        return _invalid("profile_names must contain at least two ordered sketch names.")
    profiles = []
    for name in profile_names:
        profile = service._get_sketch(str(name or ""))
        if profile is None:
            return _invalid(f"Loft profile not found by exact internal name: {name}")
        profiles.append(profile)
    if len({profile.Name for profile in profiles}) != len(profiles):
        return _invalid("profile_names contains a duplicate sketch.")
    body = service._partdesign_body_for_feature(profiles[0])
    if body is None:
        return _invalid(f"Profile {profiles[0].Name} has no unambiguous owning Body.")
    ownership = {
        profile.Name: getattr(service._partdesign_body_for_feature(profile), "Name", None)
        for profile in profiles
    }
    if any(owner != body.Name for owner in ownership.values()):
        return _invalid(
            "Every loft profile must already belong to the same PartDesign Body.",
            profile_ownership=ownership,
        )
    profile_states = {
        profile.Name: service._sketch_profile_status(profile) for profile in profiles
    }
    invalid_profiles = [
        name
        for name, state in profile_states.items()
        if not state.get("ready_for_loft_section")
    ]
    if invalid_profiles:
        return _invalid(
            "Every loft section must be a closed face-buildable sketch.",
            invalid_profiles=invalid_profiles,
            profile_states=profile_states,
        )
    section_preflight = domain_runtime.ordered_section_preflight(service, profiles)
    if not section_preflight.get("ok"):
        return _invalid(
            "Ordered loft sections do not have compatible native wire structure or distinct planes.",
            section_preflight=section_preflight,
        )
    tip_block = domain_runtime.invalid_partdesign_tip(body)
    if tip_block is not None:
        return _invalid(
            "The profile Body has an invalid or zero-effect Tip.",
            tip_state=tip_block,
        )
    body_shape_before = domain_runtime.shape_summary(body)
    if operation == "subtractive_loft" and int(body_shape_before.get("solids", 0) or 0) == 0:
        return _invalid(
            f"Body {body.Name} has no solid for a subtractive loft.",
            body_shape=body_shape_before,
        )

    def create() -> dict[str, Any]:
        import FreeCAD as App

        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("No active document.")
        target_profiles = [service._get_sketch(profile.Name) for profile in profiles]
        if any(profile is None for profile in target_profiles):
            raise RuntimeError("One or more loft profiles no longer exist.")
        target_body = service._partdesign_body_for_feature(target_profiles[0])
        if target_body is None or target_body.Name != body.Name:
            raise RuntimeError("Loft profile ownership changed before execution.")
        if any(service._partdesign_body_for_feature(item) is not target_body for item in target_profiles):
            raise RuntimeError("Loft profiles are no longer owned by one Body.")
        native_name = "AdditiveLoft" if operation == "additive_loft" else "SubtractiveLoft"
        loft = target_body.newObject(type_id, native_name)
        loft.Label = clean_label
        loft.Profile = target_profiles[0]
        loft.Sections = target_profiles[1:]
        loft.Closed = bool(closed)
        loft.Ruled = bool(ruled)
        loft.Reversed = bool(reversed)
        loft.Midplane = bool(midplane)
        loft.Refine = bool(refine)
        target_body.Tip = loft
        doc.recompute()
        effect = domain_runtime.finalize_partdesign_feature_effect(
            doc,
            target_body,
            loft,
            operation,
            body_shape_before,
        )
        return {
            "document": doc.Name,
            "body": target_body.Name,
            "profile": target_profiles[0].Name,
            "sections": [profile.Name for profile in target_profiles[1:]],
            "section_preflight": section_preflight,
            "feature": loft.Name,
            "feature_label": loft.Label,
            "feature_type": loft.TypeId,
            "closed": bool(loft.Closed),
            "ruled": bool(loft.Ruled),
            "reversed": bool(loft.Reversed),
            "midplane": bool(loft.Midplane),
            "body_group": [item.Name for item in list(target_body.Group)],
            "body_tip": getattr(getattr(target_body, "Tip", None), "Name", None),
            "base_feature": getattr(getattr(loft, "BaseFeature", None), "Name", None),
            **effect,
        }

    transaction = run_freecad_transaction(
        f"Create PartDesign {operation}: {clean_label}",
        create,
    )
    return domain_runtime.partdesign_feature_response(
        service,
        transaction,
        operation=operation,
        profile_status={
            "profiles": profile_states,
            "section_preflight": section_preflight,
        },
    )


def _invalid(message: str, **details: Any) -> dict[str, Any]:
    return {"ok": False, "error": message, "retry_same_call": False, **details}
