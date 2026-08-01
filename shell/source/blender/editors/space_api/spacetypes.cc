/* SPDX-FileCopyrightText: 2008 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup spapi
 */

#include <cstdlib>

#include "MEM_guardedalloc.h"

#include "DNA_windowmanager_types.h"

#include "BLI_listbase.hh"

#include "BKE_context.hh"
#include "BKE_screen.hh"

#include "GPU_state.hh"

#include "UI_interface.hh"
#include "UI_view2d.hh"

#include "ED_anim_api.hh"
#include "ED_armature.hh"
#include "ED_asset.hh"
#include "ED_clip.hh"
#include "ED_curve.hh"
#include "ED_curves.hh"
#include "ED_curves_sculpt.hh"
#include "ED_fileselect.hh"
#include "ED_geometry.hh"
#include "ED_gizmo_library.hh"
#include "ED_gpencil_legacy.hh"
#include "ED_grease_pencil.hh"
#include "ED_lattice.hh"
#include "ED_markers.hh"
#include "ED_mask.hh"
#include "ED_mball.hh"
#include "ED_mesh.hh"
#include "ED_node.hh"
#include "ED_object.hh"
#include "ED_paint.hh"
#include "ED_physics.hh"
#include "ED_pointcloud.hh"
#include "ED_render.hh"
#include "ED_scene.hh"
#include "ED_screen.hh"
#include "ED_sculpt.hh"
#include "ED_sequencer.hh"
#include "ED_sound.hh"
#include "ED_space_api.hh"
#include "ED_transform.hh"
#include "ED_userpref.hh"
#include "ED_util.hh"
#include "ED_uvedit.hh"

#include "io_ops.hh"

namespace blender {

void ED_spacetypes_init()
{
  using namespace blender::ed;
  /* UI unit is a variable, may be used in some space type initialization. */
  U.widget_unit = 20;

  /* Create space types. */
  /* Only the editors Cadex ships. An unregistered space type is not offered
   * in the editor menu (rna_Area_ui_type_itemf), so this list *is* the menu.
   * Not registered: space_action, space_clip, space_graph, space_image,
   * space_nla, space_script, space_sequencer, space_spreadsheet.
   * They are still *compiled* -- kept subsystems reference symbols across all
   * eight, so dropping them from the build is the delete half of the protocol
   * in docs/FREECAD.md S3 and belongs to Phase 13b. See ADR-036.
   *
   * space_node left that list in ADR-066, and the rule above is what makes
   * that safe rather than a reversal: a node tree type is a *subtype* of
   * SPACE_NODE, and the menu lists subtypes rather than the space, so
   * registering the space offers exactly the tree types that survive
   * rna_SpaceNodeEditor_tree_type_poll. That poll is filtered to Cadex trees,
   * so the menu gains one row -- "Wiring" -- and the four stock trees stay
   * off it while staying registered, which materials still need. */
  ED_spacetype_node();
  ED_spacetype_outliner();
  ED_spacetype_view3d();
  ED_spacetype_buttons();
  ED_spacetype_info();
  ED_spacetype_file();
  ED_spacetype_text();
  ED_spacetype_console();
  ED_spacetype_userpref();
  ED_spacetype_project();
  ED_spacetype_cadex_chat();
  ED_spacetype_cadex_params();
  ED_spacetype_statusbar();
  ED_spacetype_topbar();

  /* Register operator types for screen and all spaces. */
  ED_operatortypes_userpref();
  ED_operatortypes_workspace();
  ED_operatortypes_scene();
  ED_operatortypes_screen();
  ED_operatortypes_anim();
  ED_operatortypes_animchannels();
  asset::operatortypes_asset();
  ED_operatortypes_gpencil_legacy();
  ED_operatortypes_grease_pencil();
  object::operatortypes_object();
  ED_operatortypes_lattice();
  ED_operatortypes_mesh();
  geometry::operatortypes_geometry();
  sculpt_paint::operatortypes_sculpt();
  ED_operatortypes_sculpt_curves();
  ED_operatortypes_uvedit();
  ED_operatortypes_paint();
  ED_operatortypes_physics();
  ED_operatortypes_curve();
  curves::operatortypes_curves();
  pointcloud::operatortypes_pointcloud();
  ED_operatortypes_armature();
  ED_operatortypes_marker();
  ED_operatortypes_metaball();
  ED_operatortypes_sound();
  ED_operatortypes_render();
  ED_operatortypes_mask();
  ED_operatortypes_io();
  ED_operatortypes_edutils();

  ui::ED_operatortypes_view2d();
  ui::operatortypes_ui();

  ED_screen_user_menu_register();

  ui::uilisttypes_ui();

  /* Gizmo types. */
  ED_gizmotypes_button_2d();
  ED_gizmotypes_dial_3d();
  ED_gizmotypes_move_3d();
  ED_gizmotypes_arrow_3d();
  ED_gizmotypes_preselect_3d();
  ED_gizmotypes_primitive_3d();
  ED_gizmotypes_blank_3d();
  ED_gizmotypes_cage_2d();
  ED_gizmotypes_cage_3d();
  ED_gizmotypes_snap_3d();

  /* Register types for operators and gizmos. */
  for (const std::unique_ptr<SpaceType> &type : BKE_spacetypes_list()) {
    /* Initialize gizmo types first, operator types need them. */
    if (type->gizmos) {
      type->gizmos();
    }
    if (type->operatortypes) {
      type->operatortypes();
    }
  }
}

void ED_spacemacros_init()
{
  using namespace blender::ed;
  /* Macros must go last since they reference other operators.
   * They need to be registered after python operators too. */
  ED_operatormacros_armature();
  ED_operatormacros_mesh();
  ED_operatormacros_uvedit();
  ED_operatormacros_metaball();
  object::operatormacros_object();
  ED_operatormacros_file();
  ED_operatormacros_curve();
  curves::operatormacros_curves();
  pointcloud::operatormacros_pointcloud();
  ED_operatormacros_mask();
  ED_operatormacros_paint();
  ED_operatormacros_grease_pencil();

  /* A space type's own operators are registered from its `operatortypes`
   * callback, which only runs for registered space types. The macros below
   * chain those operators, so defining them for an editor Cadex does not
   * register would build macros around operators that do not exist -- which
   * WM_operatortype_macro_define survives, but only by warning on every
   * missing property at startup. See ADR-036. */
  if (BKE_spacetype_from_id(SPACE_NODE)) {
    ED_operatormacros_node();
  }
  if (BKE_spacetype_from_id(SPACE_GRAPH)) {
    ED_operatormacros_graph();
  }
  if (BKE_spacetype_from_id(SPACE_ACTION)) {
    ED_operatormacros_action();
  }
  if (BKE_spacetype_from_id(SPACE_CLIP)) {
    ED_operatormacros_clip();
  }
  if (BKE_spacetype_from_id(SPACE_SEQ)) {
    vse::ED_operatormacros_sequencer();
  }
  if (BKE_spacetype_from_id(SPACE_NLA)) {
    ED_operatormacros_nla();
  }

  /* Register dropboxes (can use macros). */
  ui::dropboxes_ui();
  for (const std::unique_ptr<SpaceType> &type : BKE_spacetypes_list()) {
    if (type->dropboxes) {
      type->dropboxes();
    }
  }
}

void ED_spacetypes_keymap(wmKeyConfig *keyconf)
{
  using namespace blender::ed;
  ED_keymap_screen(keyconf);
  ED_keymap_anim(keyconf);
  ED_keymap_animchannels(keyconf);
  ED_keymap_gpencil_legacy(keyconf);
  ED_keymap_grease_pencil(keyconf);
  object::keymap_object(keyconf);
  ED_keymap_lattice(keyconf);
  ED_keymap_mesh(keyconf);
  ED_keymap_uvedit(keyconf);
  ED_keymap_curve(keyconf);
  curves::keymap_curves(keyconf);
  pointcloud::keymap_pointcloud(keyconf);
  ED_keymap_armature(keyconf);
  ED_keymap_physics(keyconf);
  ED_keymap_metaball(keyconf);
  ED_keymap_paint(keyconf);
  ED_keymap_mask(keyconf);
  ED_keymap_marker(keyconf);
  sculpt_paint::keymap_sculpt(keyconf);

  ui::ED_keymap_view2d(keyconf);
  ui::keymap_ui(keyconf);

  transform::keymap_transform(keyconf);

  for (const std::unique_ptr<SpaceType> &type : BKE_spacetypes_list()) {
    if (type->keymap) {
      type->keymap(keyconf);
    }
  }
}

/* ********************** Custom Draw Call API ***************** */

struct RegionDrawCB {
  RegionDrawCB *next, *prev;

  void (*draw)(const bContext *, ARegion *, void *);
  void *customdata;

  int type;
};

void *ED_region_draw_cb_activate(ARegionType *art,
                                 void (*draw)(const bContext *, ARegion *, void *),
                                 void *customdata,
                                 int type)
{
  RegionDrawCB *rdc = MEM_new_zeroed<RegionDrawCB>(__func__);

  BLI_addtail(&art->drawcalls, rdc);
  rdc->draw = draw;
  rdc->customdata = customdata;
  rdc->type = type;

  return rdc;
}

bool ED_region_draw_cb_exit(ARegionType *art, void *handle)
{
  for (RegionDrawCB &rdc : art->drawcalls) {
    if (&rdc == static_cast<RegionDrawCB *>(handle)) {
      BLI_remlink(&art->drawcalls, &rdc);
      MEM_delete(&rdc);
      return true;
    }
  }
  return false;
}

static void ed_region_draw_cb_draw(const bContext *C, ARegion *region, ARegionType *art, int type)
{
  for (RegionDrawCB &rdc : art->drawcalls.items_mutable()) {
    if (rdc.type == type) {
      rdc.draw(C, region, rdc.customdata);
    }
  }
}

void ED_region_draw_cb_draw(const bContext *C, ARegion *region, int type)
{
  ed_region_draw_cb_draw(C, region, region->runtime->type, type);
}

void ED_region_surface_draw_cb_draw(const bContext *C, ARegionType *art, int type)
{
  ed_region_draw_cb_draw(C, nullptr, art, type);
}

void ED_region_draw_cb_remove_by_type(ARegionType *art, void *draw_fn, void (*free)(void *))
{
  for (RegionDrawCB &rdc : art->drawcalls.items_mutable()) {
    if (rdc.draw == draw_fn) {
      if (free) {
        free(rdc.customdata);
      }
      BLI_remlink(&art->drawcalls, &rdc);
      MEM_delete(&rdc);
    }
  }
}

}  // namespace blender
