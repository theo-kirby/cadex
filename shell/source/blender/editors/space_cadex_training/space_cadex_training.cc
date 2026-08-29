/* SPDX-FileCopyrightText: 2026 Cadex Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup spcadextraining
 *
 * The Cadex Training editor: dispatching a run to a GPU box and watching the
 * curve come back.
 *
 * One of the four editors ADR-108 split out of `SPACE_CADEX_PARAMS`, which
 * carried all five Cadex panel groups until the ask became four
 * independently arrangeable workspaces. Structurally it is
 * `space_cadex_params.cc` with the names changed, and deliberately so: the
 * sixteen touch points a new Cadex editor costs are listed in
 * `docs/BLENDER-TREE.md` section 2b, and a fifth one should be a checklist
 * rather than a design.
 *
 * Two regions and nothing else -- #RGN_TYPE_WINDOW for the panels and a
 * header. Its content comes from panels registered by the `mesh_agent`
 * add-on, and it holds **no space data of its own**: everything stateful
 * lives in `Scene` or the window manager, which is what keeps this struct a
 * bare `SpaceLink` header and keeps saved `.blend` files readable by a
 * build that predates it.
 */

#include "BLI_listbase.hh"
#include "BLI_string.hh"

#include "BKE_screen.hh"

#include "ED_screen.hh"
#include "ED_space_api.hh"

#include "DNA_space_types.h"

#include "MEM_guardedalloc.h"

#include "WM_api.hh"
#include "WM_types.hh"

#include "UI_interface.hh"
#include "UI_view2d.hh"

#include "BLO_read_write.hh"

namespace blender {

static SpaceLink *cadex_training_create(const ScrArea * /*area*/, const Scene * /*scene*/)
{
  SpaceCadexTraining *space = MEM_new<SpaceCadexTraining>("cadex training space");
  space->spacetype = SPACE_CADEX_TRAINING;

  {
    /* Header. */
    ARegion *region = BKE_area_region_new();
    BLI_addtail(&space->regionbase, region);
    region->regiontype = RGN_TYPE_HEADER;
    /* Always on top, like the other panel-column editors -- see
     * BKE_screen_header_alignment_reset(), which pins the same set. */
    region->alignment = RGN_ALIGN_TOP;
  }

  {
    /* Main region: the panels. */
    ARegion *region = BKE_area_region_new();
    BLI_addtail(&space->regionbase, region);
    region->regiontype = RGN_TYPE_WINDOW;
  }

  return (SpaceLink *)space;
}

static void cadex_training_free(SpaceLink * /*sl*/) {}

static void cadex_training_init(wmWindowManager * /*wm*/, ScrArea * /*area*/) {}

static SpaceLink *cadex_training_duplicate(SpaceLink *sl)
{
  SpaceCadexTraining *space = MEM_dupalloc(reinterpret_cast<SpaceCadexTraining *>(sl));

  return (SpaceLink *)space;
}

static void cadex_training_blend_write(BlendWriter *writer, SpaceLink *sl)
{
  writer->write_struct_cast<SpaceCadexTraining>(sl);
}

static void cadex_training_operatortypes() {}

static void cadex_training_keymap(wmKeyConfig * /*keyconf*/) {}

/* -------------------------------------------------------------------- */
/** \name Main Region
 * \{ */

static void cadex_training_main_region_init(wmWindowManager *wm, ARegion *region)
{
  region->v2d.scroll = V2D_SCROLL_RIGHT | V2D_SCROLL_VERTICAL_HIDE;

  ED_region_panels_init(wm, region);
}

static void cadex_training_main_region_listener(const wmRegionListenerParams *params)
{
  ARegion *region = params->region;
  const wmNotifier *wmn = params->notifier;

  switch (wmn->category) {
    case NC_SCENE:
    case NC_SPACE:
    case NC_WM:
      ED_region_tag_redraw(region);
      break;
  }
}

/** \} */

/* -------------------------------------------------------------------- */
/** \name Header Region
 * \{ */

static void cadex_training_header_region_init(wmWindowManager * /*wm*/, ARegion *region)
{
  ED_region_header_init(region);
}

static void cadex_training_header_region_draw(const bContext *C, ARegion *region)
{
  ED_region_header(C, region);
}

/** \} */

void ED_spacetype_cadex_training()
{
  std::unique_ptr<SpaceType> st = std::make_unique<SpaceType>();
  ARegionType *art;

  st->spaceid = SPACE_CADEX_TRAINING;
  STRNCPY(st->name, "Cadex Training");

  st->create = cadex_training_create;
  st->free = cadex_training_free;
  st->init = cadex_training_init;
  st->duplicate = cadex_training_duplicate;
  st->operatortypes = cadex_training_operatortypes;
  st->keymap = cadex_training_keymap;
  st->blend_write = cadex_training_blend_write;

  /* regions: main window */
  art = MEM_new_zeroed<ARegionType>("spacetype cadex training region");
  art->regionid = RGN_TYPE_WINDOW;
  art->init = cadex_training_main_region_init;
  art->layout = ED_region_panels_layout;
  art->draw = ED_region_panels_draw;
  art->listener = cadex_training_main_region_listener;
  art->keymapflag = ED_KEYMAP_UI;

  BLI_addhead(&st->regiontypes, art);

  /* regions: header */
  art = MEM_new_zeroed<ARegionType>("spacetype cadex training region");
  art->regionid = RGN_TYPE_HEADER;
  art->prefsizey = HEADERY;
  art->keymapflag = ED_KEYMAP_UI | ED_KEYMAP_VIEW2D | ED_KEYMAP_HEADER;
  art->init = cadex_training_header_region_init;
  art->draw = cadex_training_header_region_draw;

  BLI_addhead(&st->regiontypes, art);

  BKE_spacetype_register(std::move(st));
}

}  // namespace blender
