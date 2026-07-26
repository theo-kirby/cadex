# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Chat panel in the 3D Viewport sidebar, plus its operators.

The parameters live in their own screen area rather than in the chat column
-- see PARAMS_CONTEXT below.
"""

import os
import textwrap
import traceback

import bpy
from bpy.types import Operator, Panel

from . import agent as agent_module

# The parameters area is a second Properties editor split off the bottom of
# the viewport. It is an *area* and not another panel in the chat column
# because that is what makes it closable and reopenable on its own, like the
# viewport: a panel is a resident of someone else's region and comes and goes
# with it.
#
# It is pinned to the **Tool** tab, the same as the chat column, and the two
# panels sort themselves out by area (see _column_role). Any other tab would
# do for hosting a panel, but only Tool is free of Blender's own C-registered
# `PROPERTIES_PT_context` breadcrumb -- its poll is literally
# `sbuts->mainb != BCONTEXT_TOOL` (`buttons_context.cc`), and being a C panel
# it is not in `bpy.types`, so it cannot be polled out from Python the way the
# app template hides the inherited Python panels. On the Scene tab it puts a
# stray "Scene" row above the sliders.
PARAMS_CONTEXT = 'TOOL'

# Fraction of the viewport's height the parameters area takes. Measured from
# the bottom, and <= 0.5 on purpose: `area_split` (screen_edit.cc) gives the
# *new* area the bottom half only in that case, which is what lets
# open_params_area() tell the two halves apart without waiting for the screen
# geometry to settle.
PARAMS_SPLIT = 0.3

# The message box is a text-box widget (multi-line, wrapping, with a grip on
# its edge), and it gets its own short area at the bottom of the chat column
# for the same reason the parameters have one: only an area stays put while
# the transcript beside it scrolls. It cannot simply be a taller chat input
# bar -- that bar is a header region, header regions are one row tall by
# construction, and `ED_region_header_layout` only ever recomputes their
# *width* (`editors/screen/area.cc`). The button row stays in the header, now
# the input strip's, one row under the box.
INPUT_LINES = 3
# Three text lines, the panel padding around them, and that header row.
INPUT_AREA_UNITS = INPUT_LINES + 3.0

# Areas of the same column share an x exactly; a few pixels of slack in case
# a split leaves them off by one.
_COLUMN_SLACK = 4


class MESH_AGENT_OT_chat_send(Operator):
    bl_idname = "mesh_agent.chat_send"
    bl_label = "Send"
    bl_description = "Send the message to the assistant"

    @classmethod
    def poll(cls, context):
        return not agent_module.get_agent().busy

    def execute(self, context):
        wm = context.window_manager
        prompt = wm.mesh_chat_input
        agent = agent_module.get_agent()
        if agent.start_turn(prompt):
            wm.mesh_chat_input = ""
        return {'FINISHED'}


class MESH_AGENT_OT_chat_cancel(Operator):
    bl_idname = "mesh_agent.chat_cancel"
    bl_label = "Stop"
    bl_description = "Cancel the current assistant turn"

    @classmethod
    def poll(cls, context):
        return agent_module.get_agent().busy

    def execute(self, context):
        agent_module.get_agent().cancel()
        return {'FINISHED'}


class MESH_AGENT_OT_attach_image(Operator):
    bl_idname = "mesh_agent.attach_image"
    bl_label = "Attach Image"
    bl_description = "Attach an image file to your next message"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(
        default="*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tif;*.tiff;*.exr",
        options={'HIDDEN'})

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if agent_module.get_agent().attach_image(self.filepath) < 0:
            self.report({'WARNING'}, "Could not read image file")
            return {'CANCELLED'}
        return {'FINISHED'}


class MESH_AGENT_OT_paste_image(Operator):
    bl_idname = "mesh_agent.paste_image"
    bl_label = "Paste Image"
    bl_description = "Attach the image on the clipboard to your next message"

    def execute(self, context):
        import subprocess
        import sys
        import tempfile

        if sys.platform != "darwin":
            self.report({'WARNING'},
                        "Clipboard image paste is only supported on macOS "
                        "for now; use Attach Image instead")
            return {'CANCELLED'}

        handle, path = tempfile.mkstemp(suffix=".png", prefix="mesh_paste_")
        os.close(handle)
        script = (
            'set png_data to the clipboard as «class PNGf»\n'
            'set out_file to open for access POSIX file "{:s}" '
            'with write permission\n'
            'write png_data to out_file\n'
            'close access out_file'.format(path))
        result = subprocess.run(["osascript", "-e", script],
                                capture_output=True, timeout=10)
        if result.returncode != 0 or not os.path.getsize(path):
            os.remove(path)
            self.report({'WARNING'}, "No image on the clipboard")
            return {'CANCELLED'}
        if agent_module.get_agent().attach_image(path) < 0:
            self.report({'WARNING'}, "Could not read the pasted image")
            return {'CANCELLED'}
        return {'FINISHED'}


class MESH_AGENT_OT_adopt_script(Operator):
    bl_idname = "mesh_agent.adopt_script"
    bl_label = "Rebuild From Saved Script"
    bl_description = ("Re-run the script saved in this .blend into this "
                      "file's engine project, which is empty")

    @classmethod
    def poll(cls, context):
        return not agent_module.get_agent().busy

    def execute(self, context):
        from . import cadex_backend
        ok, report = cadex_backend.adopt_saved_script(context.scene)
        agent = agent_module.get_agent()
        if not ok:
            agent.history.add("status", report)
            self.report({'WARNING'}, "Could not rebuild from the saved script")
            return {'CANCELLED'}
        agent.history.add("status",
                          "Rebuilt this file's engine project from the script "
                          "saved in the file.")
        return {'FINISHED'}


class MESH_AGENT_OT_chat_new(Operator):
    bl_idname = "mesh_agent.chat_new"
    bl_label = "New Chat"
    bl_description = ("Start a new conversation: clear the transcript and "
                      "begin a fresh assistant session. The model in the "
                      "file is left alone")

    @classmethod
    def poll(cls, context):
        return not agent_module.get_agent().busy

    def execute(self, context):
        if not agent_module.get_agent().new_conversation():
            return {'CANCELLED'}
        return {'FINISHED'}


_ROLE_ICONS = {
    "user": 'USER',
    "assistant": 'LIGHT',
    "status": 'INFO',
}


def _area_roles(screen):
    """Role by area pointer for every Properties area on the screen.

    Found by geometry, not by which tab they are pinned to. All three are
    pinned to Tool, and the header carries a tab dropdown, so `space.context`
    is user-switchable -- keying off it would take the chat away exactly when
    the user needs it to switch back.

    The right-most column is the chat: the transcript on top, the input strip
    under it. Any Properties area outside that column is the parameters.
    """
    props = [area for area in screen.areas if area.type == 'PROPERTIES']
    if not props:
        return {}
    right = max(area.x for area in props)
    roles = {}
    column = []
    for area in props:
        if area.x >= right - _COLUMN_SLACK:
            column.append(area)
        else:
            roles[area.as_pointer()] = 'params'
    top = max(column, key=lambda area: area.y).as_pointer()
    for area in column:
        roles[area.as_pointer()] = 'chat' if area.as_pointer() == top else 'input'
    return roles


def _area_with_role(screen, role):
    roles = _area_roles(screen)
    for area in screen.areas:
        if roles.get(area.as_pointer()) == role:
            return area
    return None


def chat_area(screen):
    """The transcript: the top of the chat column."""
    return _area_with_role(screen, 'chat')


def input_area(screen):
    """The input strip under the transcript, or None if it isn't open."""
    return _area_with_role(screen, 'input')


def params_area(screen):
    """The parameters area: the Properties area outside the chat column."""
    return _area_with_role(screen, 'params')


def _column_role(context):
    """Which of our columns the region being drawn belongs to.

    'sidebar' is a real 3D-viewport sidebar, which gets the transcript, the
    parameters and an inline input -- it has no header of ours to put the
    input strip's contents in.
    """
    area = getattr(context, "area", None)
    if area is None or area.type != 'PROPERTIES':
        return 'sidebar'
    return _area_roles(context.screen).get(area.as_pointer(), 'chat')


# (window, area pointer, attempts) while the parameters area's space data is
# still catching up with its area type; see _configure_params_area.
_params_pending = []


def _configure_params_area():
    """Pin the parameters area to its tab and strip its chrome.

    Runs from a timer: assigning `area.type` swaps the space in, but
    `area.spaces.active` can still be the outgoing space for a tick, so this
    re-derives the state each time and retries -- the same reason the app
    template's layout pass is a timer.

    The area is found by the pointer open_params_area recorded, not by
    params_area(): the new area's geometry has not settled yet, so anything
    that compares x could still mistake it for the chat column and pin *that*
    to the Scene tab.
    """
    if not _params_pending:
        return None
    window, pointer, attempts = _params_pending[0]
    if attempts > 20:
        _params_pending.clear()
        return None
    _params_pending[0] = (window, pointer, attempts + 1)
    try:
        screen = window.screen
        area = next((a for a in screen.areas if a.as_pointer() == pointer),
                    None)
        if area is None:
            _params_pending.clear()
            return None
        space = area.spaces.active
        if getattr(space, "type", "") != 'PROPERTIES':
            return 0.1
        with bpy.context.temp_override(window=window, screen=screen,
                                       area=area):
            try:
                space.context = PARAMS_CONTEXT
            except TypeError:
                # The tab list is built from panels whose polls pass, so it
                # can still be empty this tick; retry.
                return 0.1
            # No header and no tab strip: the area is one block of sliders,
            # and the chat input bar's toggle is what opens and closes it.
            space.show_region_header = False
        nav = next((r for r in area.regions if r.type == 'NAVIGATION_BAR'),
                   None)
        if nav is not None and nav.width > 1:
            with bpy.context.temp_override(window=window, screen=screen,
                                           area=area, region=nav):
                bpy.ops.screen.region_toggle(region_type='NAVIGATION_BAR')
    except Exception:
        traceback.print_exc()
    _params_pending.clear()
    return None


def open_params_area(window):
    """Split the parameters area off the bottom of the largest viewport."""
    screen = window.screen
    if params_area(screen) is not None:
        return None
    viewports = [area for area in screen.areas if area.type == 'VIEW_3D']
    if not viewports:
        return None
    viewport = max(viewports, key=lambda area: area.width * area.height)
    before = {area.as_pointer() for area in screen.areas}
    try:
        with bpy.context.temp_override(window=window, screen=screen,
                                       area=viewport):
            bpy.ops.screen.area_split(direction='HORIZONTAL',
                                      factor=PARAMS_SPLIT)
    except RuntimeError:
        # The viewport is too short to split (area_split's minimum height).
        return None
    fresh = [area for area in screen.areas
             if area.as_pointer() not in before]
    if not fresh:
        return None
    area = fresh[0]
    # Area type changes need a window in the context; from a bare timer the
    # assignment appears to succeed but the space data never switches.
    with bpy.context.temp_override(window=window, screen=screen, area=area):
        area.type = 'PROPERTIES'
    _params_pending[:] = [(window, area.as_pointer(), 0)]
    if not bpy.app.timers.is_registered(_configure_params_area):
        bpy.app.timers.register(_configure_params_area, first_interval=0.05)
    return area


def close_params_area(window, area):
    """Close the parameters area; False if the screen would not let it go."""
    _params_pending.clear()
    try:
        with bpy.context.temp_override(window=window, screen=window.screen,
                                       area=area):
            bpy.ops.screen.area_close()
    except RuntimeError:
        # area_close's poll fails when no neighbour can absorb the space.
        return False
    return True


def open_input_area(window):
    """Split the input strip off the bottom of the chat column.

    Unlike the parameters area this needs no timer: both halves of a split
    Properties area are already Properties areas, so there is no space swap
    to wait on, and the guard below keeps the split factor at or under a
    half -- which is what makes the *new* area the bottom one
    (`area_split`, screen_edit.cc), so neither half has to be identified by
    geometry that has not settled yet.
    """
    screen = window.screen
    if input_area(screen) is not None:
        return None
    transcript = chat_area(screen)
    if transcript is None:
        return None
    scale = bpy.context.preferences.system.ui_scale or 1.0
    wanted = INPUT_AREA_UNITS * 20.0 * scale
    if transcript.height < wanted * 2.0:
        # Too short to give the input a strip of its own; the chat panel
        # notices and keeps the box inline instead.
        return None
    before = {area.as_pointer() for area in screen.areas}
    try:
        with bpy.context.temp_override(window=window, screen=screen,
                                       area=transcript):
            bpy.ops.screen.area_split(direction='HORIZONTAL',
                                      factor=wanted / transcript.height)
    except RuntimeError:
        return None
    fresh = [area for area in screen.areas
             if area.as_pointer() not in before]
    if not fresh:
        return None
    area = fresh[0]
    # The transcript keeps no header of its own any more: the buttons live in
    # the strip's header, one row under the message box.
    with bpy.context.temp_override(window=window, screen=screen,
                                   area=transcript):
        transcript.spaces.active.show_region_header = False
    nav = next((r for r in area.regions if r.type == 'NAVIGATION_BAR'), None)
    if nav is not None and nav.width > 1:
        with bpy.context.temp_override(window=window, screen=screen,
                                       area=area, region=nav):
            bpy.ops.screen.region_toggle(region_type='NAVIGATION_BAR')
    return area


class MESH_AGENT_OT_toggle_params(Operator):
    bl_idname = "mesh_agent.toggle_params"
    bl_label = "Parameters"
    bl_description = "Show or hide the parameters area"

    def execute(self, context):
        window = context.window
        area = params_area(window.screen)
        if area is None:
            if open_params_area(window) is None:
                self.report({'WARNING'}, "No room for the parameters area")
                return {'CANCELLED'}
        elif not close_params_area(window, area):
            self.report({'WARNING'}, "The parameters area cannot be closed")
            return {'CANCELLED'}
        return {'FINISHED'}


class VIEW3D_PT_mesh_params(Panel):
    # The sole occupant of the parameters area (PARAMS_CONTEXT above). Same
    # Tool category as the chat panel -- the Properties editor's Tool tab
    # mirrors the viewport's "Tool"-category sidebar panels -- so the poll is
    # what keeps it out of the chat column.
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_order = 0
    bl_label = "Parameters"

    # The poll is about *where* this draws, never about whether there is
    # anything to show. The old one hid the panel whenever the script declared
    # no parameters, which is why it came and went on its own; an empty model
    # now says so rather than leave the user looking at a blank strip.
    @classmethod
    def poll(cls, context):
        return _column_role(context) in {'params', 'sidebar'}

    def draw(self, context):
        from . import model
        layout = self.layout
        specs = model.load_specs(context.scene)
        group = getattr(context.scene, "mesh_params", None)
        if group is None or not specs:
            row = layout.row()
            row.enabled = False
            row.label(text="No parameters in this model"
                      if group is not None else "Parameters load after build",
                      icon='INFO')
            return
        column = layout.column()
        for spec in specs:
            if hasattr(group, spec["id"]):
                column.prop(group, spec["id"],
                            slider=spec["type"] in {'FLOAT', 'INT'})


class VIEW3D_PT_mesh_chat(Panel):
    # The Properties editor's Tool tab mirrors the viewport's "Tool"-category
    # sidebar panels (see WorkSpaceButtonsPanel in bl_ui/properties_workspace.py),
    # which lets the Mesh template host this panel as a full-height chat column:
    # a Properties editor pinned to the Tool tab, with the other tool panels
    # hidden while Simple mode is active. The viewport sidebar itself stays
    # closed in Simple mode, so the panel effectively appears only there.
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_options = {'HIDE_HEADER'}
    bl_label = "Chat"

    @classmethod
    def poll(cls, context):
        # Keeps the transcript out of the two areas that share this tab.
        return _column_role(context) in {'chat', 'sidebar'}

    def draw(self, context):
        layout = self.layout
        agent = agent_module.get_agent()

        # The model selector. It takes effect at the next turn; the
        # conversation itself continues. It edits the add-on preference, so it
        # is also the default for future sessions. (The mode dropdown that sat
        # above it is gone with the local modes -- ADR-030.)
        selectors = layout.column(align=True)
        prefs = agent_module.get_prefs()
        if prefs is not None:
            selectors.prop(prefs, "model", text="")

        # Face picking feeds BREP pins to the next message.
        from . import cadex_backend, cadex_pick
        pending = cadex_pick.pending_pin_count()
        selectors.operator(
            "mesh_agent.pick_pin", icon='EYEDROPPER',
            text="Pin Face" if not pending
            else "Pin Face ({:d} pinned)".format(pending))
        # One warning row, not a wall of text: the remedy lives in the
        # add-on preferences, which is where the fix is applied.
        ok, reason, _remedy = cadex_backend.preflight()
        if not ok:
            warning = layout.row()
            warning.alert = True
            warning.label(text=reason, icon='ERROR')

        # A duplicated or Save-As'd file names an engine project that does not
        # exist; the .blend still carries the script, so offer to re-run it
        # rather than leave the user with geometry nothing can edit.
        if cadex_backend.orphaned_project(context.scene):
            orphan = layout.box().column(align=True)
            orphan.label(text="This file's engine project is empty.",
                         icon='ERROR')
            orphan.operator(MESH_AGENT_OT_adopt_script.bl_idname,
                            icon='FILE_REFRESH')

        # Rough character wrap width from the region width (~7 px per char,
        # minus panel padding). blf-measured wrapping can come later.
        wrap = max(24, int(context.region.width / 7.2) - 6)

        for message in agent.history.messages[-40:]:
            if message.role == "status":
                row = layout.row()
                row.enabled = False
                row.label(text=message.text, icon='INFO')
                continue
            box = layout.box()
            column = box.column(align=True)
            first = True
            for paragraph in message.text.split("\n"):
                for line in textwrap.wrap(paragraph, wrap) or [""]:
                    if first:
                        column.label(text=line, icon=_ROLE_ICONS[message.role])
                        first = False
                    else:
                        column.label(text=line)

        if agent.busy:
            row = layout.row()
            row.label(text="Thinking…", icon='SORTTIME')
            row.operator(MESH_AGENT_OT_chat_cancel.bl_idname,
                         text="", icon='CANCEL')

        # A viewport sidebar has no header of ours, and a column too short to
        # split never got an input strip: rather than leave the user with a
        # transcript they cannot answer, the panel carries the input itself.
        if _column_role(context) != 'chat' \
                or input_area(context.screen) is None:
            inline = layout.column(align=True)
            draw_chat_input(inline, context)
            draw_chat_buttons(inline.row(align=True), context)


class VIEW3D_PT_mesh_input(Panel):
    # The sole occupant of the input strip (open_input_area above).
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_options = {'HIDE_HEADER'}
    bl_order = 0
    bl_label = "Message"

    @classmethod
    def poll(cls, context):
        return _column_role(context) == 'input'

    def draw(self, context):
        draw_chat_input(self.layout, context)


def draw_chat_input(layout, context):
    """The message box.

    A text-box widget rather than a text field: it wraps onto as many lines
    as it is tall, scrolls when the message outgrows them, and carries a grip
    on its edge for making it taller. Return sends -- the property's update
    callback does that -- and Shift+Return puts in a newline, which the
    widget handles itself (`interface_handlers.cc`, EVT_RETKEY).

    `confirm_only` is what keeps a click elsewhere from sending the draft:
    without it, ending the edit by any means commits the value, and
    committing is the only thing Python hears about. See ADR-035.
    """
    layout.textbox(context.window_manager, "mesh_chat_input",
                   initial_visible_lines=INPUT_LINES,
                   placeholder="Ask for a change",
                   confirm_only=True)


def draw_chat_buttons(layout, context):
    """The row under the message box: attachments, send/stop, new chat, and
    the parameters toggle."""
    agent = agent_module.get_agent()

    attach = layout.row(align=True)
    pending = agent.pending_attachment_count()
    attach.operator(MESH_AGENT_OT_attach_image.bl_idname, icon='FILE_IMAGE',
                    text="{:d}".format(pending) if pending else "")
    attach.operator(MESH_AGENT_OT_paste_image.bl_idname, text="",
                    icon='PASTEDOWN')

    if agent.busy:
        layout.operator(MESH_AGENT_OT_chat_cancel.bl_idname,
                        text="", icon='CANCEL')
    else:
        layout.operator(MESH_AGENT_OT_chat_send.bl_idname,
                        text="", icon='PLAY')
    # Starting over is one button, not a trash can: what the user wants back
    # is an assistant with an empty head, and that is the session as much as
    # the transcript (Agent.new_conversation).
    layout.operator(MESH_AGENT_OT_chat_new.bl_idname, text="", icon='FILE_NEW')

    # Opens and closes the parameters area. Depressed while it is open, so the
    # one button reads as the state as well as the switch.
    layout.operator(MESH_AGENT_OT_toggle_params.bl_idname, text="",
                    icon='OPTIONS',
                    depress=params_area(context.screen) is not None)


def draw_chat_input_header(self, context):
    """Replacement draw for PROPERTIES_HT_header while Simple mode is active
    (installed by the Mesh app template, which also flips the header region to
    the bottom of the area): a dropdown for the hidden properties tabs, and in
    the input strip the button row under the message box."""
    layout = self.layout

    # The other properties tabs, tucked behind a dropdown instead of the
    # navigation bar's icon strip.
    layout.prop(context.space_data, "context", text="", icon_only=True)

    # All three of our areas are Properties editors, so they share this header
    # type. Only the input strip's carries the buttons: the transcript's is
    # hidden, and the parameters area's, if the user brings it back, gets the
    # tab dropdown and nothing else.
    if _column_role(context) != 'input':
        return

    layout.separator_spacer()
    draw_chat_buttons(layout, context)


classes = (
    MESH_AGENT_OT_chat_send,
    MESH_AGENT_OT_chat_cancel,
    MESH_AGENT_OT_chat_new,
    MESH_AGENT_OT_attach_image,
    MESH_AGENT_OT_paste_image,
    MESH_AGENT_OT_adopt_script,
    MESH_AGENT_OT_toggle_params,
    VIEW3D_PT_mesh_params,
    VIEW3D_PT_mesh_chat,
    VIEW3D_PT_mesh_input,
)


def _chat_input_confirmed(self, _context):
    """Send the message when the input field is confirmed.

    This is what makes Return send: Blender commits a text field's value when
    the edit ends, and an RNA update callback is the only place Python hears
    about it. In a multi-line text box the C side already splits the two keys
    the way a chat wants -- Shift+Return inserts a newline, Return ends the
    edit (`interface_handlers.cc`, EVT_RETKEY under ButtonType::TextBox).

    Clicking outside the field ends the edit the same way, so it sends too.
    That is the whole behaviour of a Blender text button; the alternative is
    to have Return not send at all.
    """
    prompt = self.mesh_chat_input
    if not prompt.strip():
        return
    agent = agent_module.get_agent()
    if agent.busy:
        return
    if agent.start_turn(prompt):
        # Re-enters this callback with an empty value, which returns above.
        self.mesh_chat_input = ""


def register():
    bpy.types.WindowManager.mesh_chat_input = bpy.props.StringProperty(
        name="Message",
        description="Ask the assistant to build or change something",
        default="",
        update=_chat_input_confirmed,
    )
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    if bpy.app.timers.is_registered(_configure_params_area):
        bpy.app.timers.unregister(_configure_params_area)
    _params_pending.clear()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.WindowManager.mesh_chat_input
