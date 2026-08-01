# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The panels of the two Cadex editors, plus the chat operators.

The transcript, the message box and the parameter sliders are panels of
`SPACE_CADEX_CHAT` and `SPACE_CADEX_PARAMS` -- real editor types, listed in
the editor-type dropdown and dockable like the viewport. They used to be
three Properties editors pinned to the Tool tab, told apart at draw time by
comparing `area.x` and `area.y`, with every `poll()` hanging off that guess.
The space type is the answer now, so none of the polls here are about *where*
they draw. See ADR-035.

Headers live in `spaces.py`.
"""

import os
import textwrap

import bpy
from bpy.types import Operator, Panel

from . import agent as agent_module

# Fraction of the viewport's height a freshly split parameters editor takes.
PARAMS_SPLIT = 0.3

# The message box is a text-box widget: it wraps onto as many lines as it is
# tall, scrolls when the message outgrows them, and carries a grip on its edge
# for making it taller. It sits in the chat editor's RGN_TYPE_EXECUTE region,
# which -- unlike a header -- is an ordinary sizable region
# (RGN_TYPE_IS_HEADER_ANY deliberately excludes it, DNA_screen_types.h). That
# is what retired the fourth screen area ADR-034 documents.
INPUT_LINES = 3


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
    # Two callers, one meaning: push the script in this .blend to the engine.
    # The chat offers it when the engine project is empty (a duplicated or
    # Save-As'd file); the Text Editor's sidebar offers it as "Apply to Model"
    # after a hand edit, which is the only route from the buffer to the engine.
    bl_description = ("Run the script saved in this .blend into this file's "
                      "engine project")

    @classmethod
    def poll(cls, context):
        return not agent_module.get_agent().busy

    def execute(self, context):
        from . import cadex_backend
        from . import model
        ok, report = cadex_backend.adopt_saved_script(context.scene)
        agent = agent_module.get_agent()
        if not ok:
            agent.history.add("status", report)
            # So the panels can say *why* the buffer is still not in the model.
            model.record_error(report)
            self.report({'WARNING'}, "Could not rebuild from the saved script")
            return {'CANCELLED'}
        model.clear_last_error()
        agent.history.add("status",
                          "Rebuilt this file's engine project from the script "
                          "saved in the file.")
        return {'FINISHED'}


class MESH_AGENT_OT_rebuild_model(Operator):
    bl_idname = "mesh_agent.rebuild_model"
    bl_label = "Rebuild Model"
    # The user-facing half of the ADR-039 way out. Distinct from "Rebuild From
    # Saved Script", which pushes *this file's* buffer to the engine: this one
    # sends nothing and re-runs what the engine already stores, so it is the
    # safe thing to press when it is unclear which side is wrong.
    bl_description = ("Re-run the script the engine holds and re-derive the "
                      "parameters and geometry from it")

    @classmethod
    def poll(cls, context):
        return not agent_module.get_agent().busy

    def execute(self, context):
        from . import cadex_backend
        from . import model
        ok, report = cadex_backend.rebuild_model(context.scene)
        agent = agent_module.get_agent()
        if not ok:
            agent.history.add("status", report)
            model.record_error(report)
            self.report({'WARNING'}, "The engine could not re-run its script")
            return {'CANCELLED'}
        model.clear_last_error()
        agent.history.add("status", "Re-ran the stored script; parameters and "
                                    "geometry re-derived from it.")
        return {'FINISHED'}


class MESH_AGENT_OT_apply_slider_defaults(Operator):
    bl_idname = "mesh_agent.apply_slider_defaults"
    bl_label = "Apply as Defaults"
    bl_description = ("Write the current slider values into the script as the "
                      "parameters' default values")

    @classmethod
    def poll(cls, context):
        return not agent_module.get_agent().busy

    def execute(self, context):
        from . import cadex_backend
        from . import model
        ok, report = cadex_backend.apply_slider_defaults(context.scene)
        agent = agent_module.get_agent()
        if not ok:
            agent.history.add("status", report)
            model.record_error(report)
            self.report({'WARNING'}, first_line(report))
            return {'CANCELLED'}
        model.clear_last_error()
        # The per-parameter old -> new lines are the interesting part: this
        # operation edits the user's script, so it says exactly what it wrote.
        agent.history.add("status",
                          "Slider values are the script's defaults now.\n"
                          + "\n".join(report.splitlines()[1:]))
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


def first_line(report, limit=64):
    """One row's worth of an engine failure report.

    The reports are written for the model -- structured and several lines long
    -- and a panel row shows one line. The whole report is in the transcript
    and the console; this is the label on the button that fixes it.
    """
    lines = [line for line in str(report or "").splitlines() if line.strip()]
    line = lines[0].strip() if lines else ""
    return line if len(line) <= limit else line[:limit - 1] + "…"


def params_area(screen):
    """The parameters editor on this screen, or None.

    One `area.type` comparison. There is no pointer bookkeeping and no retry
    loop because there is no space-data swap to wait on.
    """
    return next((area for area in screen.areas
                 if area.type == 'CADEX_PARAMS'), None)


class MESH_AGENT_OT_toggle_params(Operator):
    bl_idname = "mesh_agent.toggle_params"
    bl_label = "Parameters"
    bl_description = "Show or hide the parameters editor"

    def execute(self, context):
        window = context.window
        screen = window.screen
        area = params_area(screen)
        if area is not None:
            try:
                with context.temp_override(window=window, screen=screen,
                                           area=area):
                    bpy.ops.screen.area_close()
            except RuntimeError:
                # area_close's poll fails when no neighbour can absorb it.
                self.report({'WARNING'},
                            "The parameters editor cannot be closed")
                return {'CANCELLED'}
            return {'FINISHED'}

        viewports = [a for a in screen.areas if a.type == 'VIEW_3D']
        if not viewports:
            self.report({'WARNING'}, "No viewport to split")
            return {'CANCELLED'}
        viewport = max(viewports, key=lambda a: a.width * a.height)
        before = {a.as_pointer() for a in screen.areas}
        try:
            with context.temp_override(window=window, screen=screen,
                                       area=viewport):
                bpy.ops.screen.area_split(direction='HORIZONTAL',
                                          factor=PARAMS_SPLIT)
        except RuntimeError:
            # The viewport is too short to split (area_split's minimum).
            self.report({'WARNING'}, "No room for the parameters editor")
            return {'CANCELLED'}
        fresh = [a for a in screen.areas if a.as_pointer() not in before]
        if not fresh:
            self.report({'WARNING'}, "No room for the parameters editor")
            return {'CANCELLED'}
        # Area type changes need a window in the context; without one the
        # assignment appears to succeed but the space data never switches.
        with context.temp_override(window=window, screen=screen,
                                   area=fresh[0]):
            fresh[0].type = 'CADEX_PARAMS'
        return {'FINISHED'}


class CADEX_PARAMS_PT_simulation(Panel):
    """Playback for a model that has a simulation, and nothing otherwise.

    Watching the mechanism move is the point of building one, and a baked
    simulation is otherwise reachable only from an editor this product does
    not show. It lives beside the sliders because that is where you already
    are when you want to see the effect of one: no new editor and no new
    space type (ADR-036 stands).

    Playing from here redraws the 3D viewport correctly --
    ``match_region_with_redraws`` tags every ``SPACE_VIEW3D`` region
    whichever region started playback.
    """

    bl_space_type = 'CADEX_PARAMS'
    bl_region_type = 'WINDOW'
    bl_label = "Simulation"

    @classmethod
    def poll(cls, context):
        from . import cadex_animate
        # One custom-property lookup: a model with no simulation sees the
        # parameters editor exactly as it was.
        return cadex_animate.SCENE_FLAG in context.scene

    def draw(self, context):
        from . import cadex_animate
        scene = context.scene
        info = dict(scene.get(cadex_animate.SCENE_FLAG) or {})
        layout = self.layout

        playing = bool(getattr(context.screen, "is_animation_playing", False))
        row = layout.row(align=True)
        row.scale_y = 1.3
        row.operator("screen.animation_play",
                     text="Pause" if playing else "Play",
                     icon='PAUSE' if playing else 'PLAY')

        layout.prop(scene, "frame_current", text="Frame")

        fps = float(info.get("fps") or scene.render.fps or 30)
        elapsed = max(0, scene.frame_current - scene.frame_start) / fps
        total = max(0, scene.frame_end - scene.frame_start) / fps
        row = layout.row()
        row.enabled = False
        row.label(text="{:.2f} s of {:.2f} s  ({:d} components)".format(
            elapsed, total, int(info.get("components") or 0)))


class CADEX_PARAMS_PT_parameters(Panel):
    """The sole occupant of the parameters editor's main region."""

    bl_space_type = 'CADEX_PARAMS'
    bl_region_type = 'WINDOW'
    bl_options = {'HIDE_HEADER'}
    bl_label = "Parameters"

    # No poll. It used to say *where* this draws; the space type says that
    # now. An empty model says so in the body rather than leaving the user
    # looking at a blank editor.

    def draw(self, context):
        from . import model
        layout = self.layout

        # A failed drag has nowhere else to surface: the debounce timer runs
        # outside any operator, so before ADR-039 a rebuild that the engine
        # refused printed to the console and the slider just appeared to do
        # nothing. The remedy sits in the same panel as the failure.
        failure = model.last_error()
        if failure:
            box = layout.box().column(align=True)
            row = box.row()
            row.alert = True
            row.label(text=first_line(failure), icon='ERROR')
            box.operator(MESH_AGENT_OT_rebuild_model.bl_idname,
                         icon='FILE_REFRESH')

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

        # Collapses the override layer: the values the sliders are sitting at
        # become the defaults *in the script*. Live only while some slider is
        # away from its declared default, so the button reads as the answer to
        # "these are the numbers I want -- keep them".
        row = layout.row()
        row.enabled = model.defaults_differ_from_sliders(context.scene)
        row.operator(MESH_AGENT_OT_apply_slider_defaults.bl_idname,
                     icon='CHECKMARK')


class CADEX_CHAT_PT_transcript(Panel):
    """The conversation, in the chat editor's main region."""

    bl_space_type = 'CADEX_CHAT'
    bl_region_type = 'WINDOW'
    bl_options = {'HIDE_HEADER'}
    bl_label = "Chat"

    # No poll: this is the chat editor, so this is where the chat goes.

    def draw(self, context):
        layout = self.layout
        agent = agent_module.get_agent()

        # The model selector and Pin Face moved to the editor's header
        # (spaces.py): they are chat-level controls, and the header is where
        # an editor's chrome belongs now that this editor has one.
        from . import cadex_backend
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


class CADEX_CHAT_PT_input(Panel):
    """The message box and its button row, in the chat editor's execute
    region -- a normal sizable region, so the box can be several rows tall
    and stay put while the transcript above it scrolls."""

    bl_space_type = 'CADEX_CHAT'
    bl_region_type = 'EXECUTE'
    bl_options = {'HIDE_HEADER'}
    bl_label = "Message"

    def draw(self, context):
        column = self.layout.column(align=True)
        draw_chat_input(column, context)
        draw_chat_buttons(column.row(align=True), context)


def draw_chat_input(layout, context):
    """The message box.

    A text-box widget rather than a text field: it wraps onto as many lines
    as it is tall, scrolls when the message outgrows them, and carries a grip
    on its edge for making it taller. Return sends -- the property's update
    callback does that -- and Shift+Return puts in a newline, which the
    widget handles itself (`interface_handlers.cc`, EVT_RETKEY).

    `confirm_only` is what keeps a click elsewhere from sending the draft:
    without it, ending the edit by any means commits the value, and
    committing is the only thing Python hears about. See ADR-034.
    """
    layout.textbox(context.window_manager, "mesh_chat_input",
                   initial_visible_lines=INPUT_LINES,
                   placeholder="Ask for a change",
                   confirm_only=True)


def draw_chat_buttons(layout, context):
    """The row under the message box: attachments, send/stop, new chat, and
    the two view toggles (parameters, script)."""
    from . import spaces
    agent = agent_module.get_agent()

    attach = layout.row(align=True)
    pending = agent.pending_attachment_count()
    attach.operator(MESH_AGENT_OT_attach_image.bl_idname, icon='FILE_IMAGE',
                    text="{:d}".format(pending) if pending else "")
    attach.operator(MESH_AGENT_OT_paste_image.bl_idname, text="",
                    icon='PASTEDOWN')

    # Measuring a terminal off the model (ADR-067). Beside the attachment
    # buttons because it is the same kind of thing -- something the user
    # gathers now and the assistant reads on the next turn -- and counted the
    # same way, so several picks visibly batch into one turn. Only offered in
    # Edit Mode on a cadex output, which is where the gesture exists.
    from . import cadex_terminal_pick

    if cadex_terminal_pick.MESH_AGENT_OT_define_terminal.poll(context):
        queued = cadex_terminal_pick.pending_terminal_count()
        attach.operator(
            cadex_terminal_pick.MESH_AGENT_OT_define_terminal.bl_idname,
            icon='SNAP_MIDPOINT',
            text="{:d}".format(queued) if queued else "")

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

    # Opens and closes the parameters editor. Depressed while it is open, so
    # the one button reads as the state as well as the switch.
    layout.operator(MESH_AGENT_OT_toggle_params.bl_idname, text="",
                    icon='OPTIONS',
                    depress=params_area(context.screen) is not None)
    # And the same for the script view -- a Text Editor pointed at the mirror.
    # It sits here rather than in the chat header (where a one-way opener used
    # to live) so the two views are one pair of buttons with one meaning.
    layout.operator(spaces.MESH_AGENT_OT_show_script.bl_idname, text="",
                    icon='TEXT',
                    depress=spaces.script_area(context.screen) is not None)


classes = (
    MESH_AGENT_OT_chat_send,
    MESH_AGENT_OT_chat_cancel,
    MESH_AGENT_OT_chat_new,
    MESH_AGENT_OT_attach_image,
    MESH_AGENT_OT_paste_image,
    MESH_AGENT_OT_adopt_script,
    MESH_AGENT_OT_rebuild_model,
    MESH_AGENT_OT_apply_slider_defaults,
    MESH_AGENT_OT_toggle_params,
    CADEX_PARAMS_PT_simulation,
    CADEX_PARAMS_PT_parameters,
    CADEX_CHAT_PT_transcript,
    CADEX_CHAT_PT_input,
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
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.WindowManager.mesh_chat_input
