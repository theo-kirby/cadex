/* SPDX-FileCopyrightText: 2026 Cadex Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup spcadexparams
 *
 * The Cadex parameters editor: the sliders the model declares.
 *
 * Two regions and nothing else -- #RGN_TYPE_WINDOW for the sliders and a
 * header. It exists as a space type rather than a panel so that it docks,
 * splits and closes like the viewport does; it was a second Properties editor
 * told apart from the chat column by comparing area coordinates, which is the
 * machinery this replaces.
 *
 * Its content comes from panels registered by the `mesh_agent` add-on. There
 * is no space data of its own: the values live in `scene.mesh_params`.
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

static SpaceLink *cadex_params_create(const ScrArea * /*area*/, const Scene * /*scene*/)
{
  SpaceCadexParams *params_space = MEM_new<SpaceCadexParams>("cadex params space");
  params_space->spacetype = SPACE_CADEX_PARAMS;

  {
    /* Header. */
    ARegion *region = BKE_area_region_new();
    BLI_addtail(&params_space->regionbase, region);
    region->regiontype = RGN_TYPE_HEADER;
    /* Always on top, like the other panel-column editors -- see
     * BKE_screen_header_alignment_reset(), which pins the same set. */
    region->alignment = RGN_ALIGN_TOP;
  }

  {
    /* Main region: the sliders. */
    ARegion *region = BKE_area_region_new();
    BLI_addtail(&params_space->regionbase, region);
    region->regiontype = RGN_TYPE_WINDOW;
  }

  return (SpaceLink *)params_space;
}

static void cadex_params_free(SpaceLink * /*sl*/) {}

static void cadex_params_init(wmWindowManager * /*wm*/, ScrArea * /*area*/) {}

static SpaceLink *cadex_params_duplicate(SpaceLink *sl)
{
  SpaceCadexParams *space_params = MEM_dupalloc(reinterpret_cast<SpaceCadexParams *>(sl));

  return (SpaceLink *)space_params;
}

static void cadex_params_blend_write(BlendWriter *writer, SpaceLink *sl)
{
  writer->write_struct_cast<SpaceCadexParams>(sl);
}

static void cadex_params_operatortypes() {}

static void cadex_params_keymap(wmKeyConfig * /*keyconf*/) {}

/* -------------------------------------------------------------------- */
/** \name Main Region
 * \{ */

static void cadex_params_main_region_init(wmWindowManager *wm, ARegion *region)
{
  region->v2d.scroll = V2D_SCROLL_RIGHT | V2D_SCROLL_VERTICAL_HIDE;

  ED_region_panels_init(wm, region);
}

static void cadex_params_main_region_listener(const wmRegionListenerParams *params)
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

static void cadex_params_header_region_init(wmWindowManager * /*wm*/, ARegion *region)
{
  ED_region_header_init(region);
}

static void cadex_params_header_region_draw(const bContext *C, ARegion *region)
{
  ED_region_header(C, region);
}

/** \} */

void ED_spacetype_cadex_params()
{
  std::unique_ptr<SpaceType> st = std::make_unique<SpaceType>();
  ARegionType *art;

  st->spaceid = SPACE_CADEX_PARAMS;
  STRNCPY(st->name, "Cadex Parameters");

  st->create = cadex_params_create;
  st->free = cadex_params_free;
  st->init = cadex_params_init;
  st->duplicate = cadex_params_duplicate;
  st->operatortypes = cadex_params_operatortypes;
  st->keymap = cadex_params_keymap;
  st->blend_write = cadex_params_blend_write;

  /* regions: main window */
  art = MEM_new_zeroed<ARegionType>("spacetype cadex params region");
  art->regionid = RGN_TYPE_WINDOW;
  art->init = cadex_params_main_region_init;
  art->layout = ED_region_panels_layout;
  art->draw = ED_region_panels_draw;
  art->listener = cadex_params_main_region_listener;
  art->keymapflag = ED_KEYMAP_UI;

  BLI_addhead(&st->regiontypes, art);

  /* regions: header */
  art = MEM_new_zeroed<ARegionType>("spacetype cadex params region");
  art->regionid = RGN_TYPE_HEADER;
  art->prefsizey = HEADERY;
  art->keymapflag = ED_KEYMAP_UI | ED_KEYMAP_VIEW2D | ED_KEYMAP_HEADER;
  art->init = cadex_params_header_region_init;
  art->draw = cadex_params_header_region_draw;

  BLI_addhead(&st->regiontypes, art);

  BKE_spacetype_register(std::move(st));
}

}  // namespace blender
