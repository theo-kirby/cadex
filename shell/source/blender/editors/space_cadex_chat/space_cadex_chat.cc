/* SPDX-FileCopyrightText: 2026 Cadex Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup spcadexchat
 *
 * The Cadex chat editor: the conversation with the assistant.
 *
 * Three regions, and the middle one is the whole point:
 *
 * - #RGN_TYPE_WINDOW  the transcript, a panel region that scrolls.
 * - #RGN_TYPE_EXECUTE the message box and its button row.
 * - #RGN_TYPE_HEADER  the model selector and the chat-level buttons.
 *
 * The message box used to live in a screen *area* of its own, because a
 * header region is one row tall by construction and the box needs several.
 * #RGN_TYPE_EXECUTE is not covered by #RGN_TYPE_IS_HEADER_ANY, so it is an
 * ordinary panel region: the input is a region of this editor now, and the
 * fourth area -- and the geometry guessing that told the areas apart -- is
 * gone. Like the project editor's execute region it is #RGN_FLAG_DYNAMIC_SIZE:
 * a fixed-height region left the input floating over dead rows of region, and
 * hugging the content is what puts the box at the bottom of the window.
 * Dragging the message box taller is still wanted here, and the box's own
 * grip provides it -- more visible lines is more content, and the region
 * follows.
 *
 * The editor is deliberately empty of C-side content. Everything drawn in it
 * comes from panels registered by the `mesh_agent` add-on (`spaces.py`,
 * `ui.py`), which is where UI belongs.
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

/** Message box plus its button row: three text lines and the padding. */
#define CADEX_CHAT_EXECUTE_ROWS 6

static SpaceLink *cadex_chat_create(const ScrArea * /*area*/, const Scene * /*scene*/)
{
  SpaceCadexChat *chat_space = MEM_new<SpaceCadexChat>("cadex chat space");
  chat_space->spacetype = SPACE_CADEX_CHAT;

  {
    /* Header. */
    ARegion *region = BKE_area_region_new();
    BLI_addtail(&chat_space->regionbase, region);
    region->regiontype = RGN_TYPE_HEADER;
    /* Always on top, like the other panel-column editors -- see
     * BKE_screen_header_alignment_reset(), which pins the same set. */
    region->alignment = RGN_ALIGN_TOP;
  }

  {
    /* Execution region: the message box. */
    ARegion *region = BKE_area_region_new();
    BLI_addtail(&chat_space->regionbase, region);
    region->regiontype = RGN_TYPE_EXECUTE;
    region->alignment = RGN_ALIGN_BOTTOM;
    region->flag |= RGN_FLAG_DYNAMIC_SIZE | RGN_FLAG_NO_USER_RESIZE;
  }

  {
    /* Main region: the transcript. */
    ARegion *region = BKE_area_region_new();
    BLI_addtail(&chat_space->regionbase, region);
    region->regiontype = RGN_TYPE_WINDOW;
  }

  return (SpaceLink *)chat_space;
}

static void cadex_chat_free(SpaceLink * /*sl*/) {}

static void cadex_chat_init(wmWindowManager * /*wm*/, ScrArea *area)
{
  /* Saved layouts -- the app template and every user file written before the
   * execute region hugged its content -- carry the region flags they were
   * saved with, so the dynamic size is enforced here rather than trusted to
   * cadex_chat_create(), the way BKE_screen_header_alignment_reset() pins
   * header alignment for the same reason. */
  for (ARegion &region : area->regionbase) {
    if (region.regiontype == RGN_TYPE_EXECUTE) {
      region.alignment = RGN_ALIGN_BOTTOM;
      region.flag |= RGN_FLAG_DYNAMIC_SIZE | RGN_FLAG_NO_USER_RESIZE;
    }
  }
}

static SpaceLink *cadex_chat_duplicate(SpaceLink *sl)
{
  SpaceCadexChat *space_chat = MEM_dupalloc(reinterpret_cast<SpaceCadexChat *>(sl));

  return (SpaceLink *)space_chat;
}

static void cadex_chat_blend_write(BlendWriter *writer, SpaceLink *sl)
{
  writer->write_struct_cast<SpaceCadexChat>(sl);
}

static void cadex_chat_operatortypes() {}

static void cadex_chat_keymap(wmKeyConfig * /*keyconf*/) {}

/* -------------------------------------------------------------------- */
/** \name Main Region (the transcript)
 * \{ */

static void cadex_chat_main_region_init(wmWindowManager *wm, ARegion *region)
{
  region->v2d.scroll = V2D_SCROLL_RIGHT | V2D_SCROLL_VERTICAL_HIDE;

  ED_region_panels_init(wm, region);
}

static void cadex_chat_main_region_listener(const wmRegionListenerParams *params)
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

static void cadex_chat_header_region_init(wmWindowManager * /*wm*/, ARegion *region)
{
  ED_region_header_init(region);
}

static void cadex_chat_header_region_draw(const bContext *C, ARegion *region)
{
  ED_region_header(C, region);
}

/** \} */

void ED_spacetype_cadex_chat()
{
  std::unique_ptr<SpaceType> st = std::make_unique<SpaceType>();
  ARegionType *art;

  st->spaceid = SPACE_CADEX_CHAT;
  STRNCPY(st->name, "Cadex Chat");

  st->create = cadex_chat_create;
  st->free = cadex_chat_free;
  st->init = cadex_chat_init;
  st->duplicate = cadex_chat_duplicate;
  st->operatortypes = cadex_chat_operatortypes;
  st->keymap = cadex_chat_keymap;
  st->blend_write = cadex_chat_blend_write;

  /* regions: main window */
  art = MEM_new_zeroed<ARegionType>("spacetype cadex chat region");
  art->regionid = RGN_TYPE_WINDOW;
  art->init = cadex_chat_main_region_init;
  art->layout = ED_region_panels_layout;
  art->draw = ED_region_panels_draw;
  art->listener = cadex_chat_main_region_listener;
  art->keymapflag = ED_KEYMAP_UI;

  BLI_addhead(&st->regiontypes, art);

  /* regions: header */
  art = MEM_new_zeroed<ARegionType>("spacetype cadex chat region");
  art->regionid = RGN_TYPE_HEADER;
  art->prefsizey = HEADERY;
  art->keymapflag = ED_KEYMAP_UI | ED_KEYMAP_VIEW2D | ED_KEYMAP_HEADER;
  art->init = cadex_chat_header_region_init;
  art->draw = cadex_chat_header_region_draw;

  BLI_addhead(&st->regiontypes, art);

  /* regions: execution window (the message box) */
  art = MEM_new_zeroed<ARegionType>("spacetype cadex chat region");
  art->regionid = RGN_TYPE_EXECUTE;
  art->prefsizey = CADEX_CHAT_EXECUTE_ROWS * HEADERY;
  art->init = ED_region_panels_init;
  art->layout = ED_region_panels_layout;
  art->draw = ED_region_panels_draw;
  art->listener = cadex_chat_main_region_listener;
  art->keymapflag = ED_KEYMAP_UI;

  BLI_addhead(&st->regiontypes, art);

  BKE_spacetype_register(std::move(st));
}

}  // namespace blender
