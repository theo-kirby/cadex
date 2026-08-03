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
from . import cadex_collision

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


class MESH_AGENT_OT_toggle_collision(Operator):
    """Show or hide the collision geometry the solver actually simulates.

    A collision shape is placed in the *component* frame and may sit outside
    the part it stands for, so nothing about the drawn solid says where it
    is. Two bugs in one model came of that (ADR-087, ADR-090) and both were
    found by arithmetic after the fact. This draws it.
    """

    bl_idname = "mesh_agent.toggle_collision"
    bl_label = "Collision Shapes"
    bl_description = ("Show or hide the collision shapes the physics solver "
                      "uses, as wire cages on the parts they belong to")

    def execute(self, context):
        from . import cadex_collision
        try:
            report = cadex_collision.toggle()
        except Exception as error:
            self.report({'WARNING'}, str(error))
            return {'CANCELLED'}
        message = str(report.get("message") or "")
        if message:
            self.report({'INFO'}, message)
        return {'FINISHED'}


class CADEX_ENV_PT_collision(Panel):
    """What the solver touches, for a model that has collision geometry.

    Polls on the scene flag exactly as the Simulation panel does, so a model
    without dynamics sees an empty Environment editor rather than a wrong
    one. Since ADR-108 this is the sole occupant of its own editor, which is
    what lets it sit open beside the viewport while the sliders sit
    elsewhere.

    The initial-contact line is the one row that would have caught the
    shipped hopper: it says what is *already touching before anything
    moves*, which is the only observable that distinguishes a collision
    shape placed where its author meant from one placed 20 mm out (ADR-087).
    """

    bl_space_type = 'CADEX_ENV'
    bl_region_type = 'WINDOW'
    bl_label = "Collision"

    @classmethod
    def poll(cls, context):
        from . import cadex_collision
        return cadex_collision.SCENE_FLAG in context.scene

    def draw(self, context):
        from . import cadex_collision
        info = dict(context.scene.get(cadex_collision.SCENE_FLAG) or {})
        layout = self.layout

        row = layout.row()
        row.label(text="{:d} shape{:s} on {:d} part{:s}".format(
            int(info.get("shapes") or 0),
            "" if int(info.get("shapes") or 0) == 1 else "s",
            int(info.get("components") or 0),
            "" if int(info.get("components") or 0) == 1 else "s"),
            icon='MESH_CUBE')

        contacts = int(info.get("contacts") or 0)
        penetrating = int(info.get("penetrating") or 0)
        if not contacts:
            layout.label(text="Nothing touching at t = 0", icon='CHECKMARK')
        else:
            box = layout.box()
            box.label(
                text="Touching at t = 0: {:d} contact{:s}".format(
                    contacts, "" if contacts == 1 else "s"),
                icon='ERROR' if penetrating else 'INFO')
            for line in info.get("contact_lines") or ():
                box.label(text=str(line))
            omitted = int(info.get("contacts_omitted") or 0)
            if omitted:
                box.label(text="...and {:d} more".format(omitted))
            if penetrating:
                box.label(text="{:d} interpenetrating".format(penetrating),
                          icon='ERROR')

        for name in info.get("skipped") or ():
            layout.label(text="not drawn: {:s}".format(str(name)),
                         icon='GHOST_DISABLED')


class CADEX_POLICY_PT_simulation(Panel):
    """Playback for a model that has a simulation, and nothing otherwise.

    Watching the mechanism move is the point of building one, and a baked
    simulation is otherwise reachable only from an editor this product does
    not show. It used to live beside the sliders, because that was where you
    already were when you wanted to see the effect of one, and because a
    readout is not worth a space type (ADR-036). ADR-108 reversed that: five
    panel groups in one editor cannot be *arranged*, and arranging them is
    most of what a person does with a workspace. It shares the Policy editor
    with Policy Outputs, which is the pairing that reads: what the policy
    did, and what it commanded.

    Playing from here redraws the 3D viewport correctly --
    ``match_region_with_redraws`` tags every ``SPACE_VIEW3D`` region
    whichever region started playback.
    """

    bl_space_type = 'CADEX_POLICY'
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


def draw_actuator_bars(layout, channels, values):
    """One row per actuator: its command against its own declared range.

    Shared by the Policy editor, which reads a recorded trace, and the Live
    editor, which reads a session running right now (ADR-108, ADR-109). The
    numbers arrive by different routes and mean exactly the same thing, so
    one loop draws both -- two copies would be two places for the
    "each bar spans its own limits" rule below to drift apart.

    Read-only by construction: ``layout.progress`` draws a bar and takes no
    input. For a recording that is right because editing one would be
    editing history; for a live session it is right because the policy is
    what decides these, not the person watching.

    ``values`` of ``None`` means *no command at this frame* -- the reset
    pose, before any action has been taken.
    """

    if not channels:
        return
    if values is None:
        # Said rather than drawn as zeros, which would be a command the
        # policy never issued.
        note = layout.row()
        note.enabled = False
        note.label(text="No command yet at this frame", icon='INFO')
        return

    column = layout.column(align=True)
    for channel, value in zip(channels, values):
        low = float(channel["low"])
        high = float(channel["high"])
        span = high - low
        factor = 0.0 if span <= 0.0 else (float(value) - low) / span
        split = column.split(factor=0.42, align=True)
        label = split.row()
        label.enabled = False
        label.label(text=str(channel["label"]))
        split.progress(
            factor=min(max(factor, 0.0), 1.0),
            text="{:+.1f} {:s}".format(float(value), str(channel["unit"])),
        )

    # Each bar is drawn against *its own* range, and the ranges need not
    # agree: a motor's comes from its effort limit and a servo's from its
    # joint limits, so they differ in span and in unit. One aggregate "full
    # scale" number would be false the first time a mechanism mixed the two
    # -- this says what is true of every row instead.
    note = layout.row()
    note.enabled = False
    note.label(text="each bar spans that actuator's own limits")


class CADEX_POLICY_PT_actuators(Panel):
    """What the policy is telling the motors, at the current frame.

    A rollout's poses already show what the mechanism *did*; this is the
    only place the shell shows what the policy *decided*. Each row is one
    actuator's command against the range the task bundle derived for it, so
    a bar pinned at an end is the policy saturating that motor -- the thing
    you would otherwise only find by reading the trace.

    Read-only by construction: ``layout.progress`` draws a bar and takes no
    input, which is right, because these numbers are a recording. Editing
    one would be editing history.

    In the **Policy** editor beside ``CADEX_POLICY_PT_simulation`` since
    ADR-108: a recording and its commands are one thing to look at. The
    drawing itself is ``draw_actuator_bars``, shared with the Live editor --
    the bars mean the same thing whether the numbers came off a trace or off
    a session running right now, and two copies of that loop would be two
    places for the "each bar spans its own limits" rule to drift.
    """

    bl_space_type = 'CADEX_POLICY'
    bl_region_type = 'WINDOW'
    bl_label = "Policy Outputs"

    @classmethod
    def poll(cls, context):
        from . import cadex_animate
        # Only a policy rollout leaves this behind; a kinematics or dynamics
        # simulation has no policy and so has nothing to draw here.
        return cadex_animate.COMMANDS_FLAG in context.scene

    def draw(self, context):
        from . import cadex_animate
        scene = context.scene
        table = scene.get(cadex_animate.COMMANDS_FLAG)
        draw_actuator_bars(
            self.layout,
            list((table or {}).get("channels") or ()),
            cadex_animate.commands_at(table, scene.frame_current),
        )


class CADEX_TRAINING_PT_training(Panel):
    """A training run that is happening on another machine, while it happens.

    Before this, a run was a black box with one artifact at the end: you
    dispatched it, waited, and found out. The mg-legs run that motivated M9
    peaked at iteration 1200 of 2000 -- roughly thirty of its seventy-six
    minutes made the policy worse, and there was no way to know that while
    it was happening or to stop it.

    What this reads is one local file, ``training-progress.json``, which
    ``training/remote_train.sh watch`` mirrors off the box. **No ssh, no
    protocol change, no engine change, and no mujoco** -- the shell may
    never import that (``test_the_shell_never_learns_about_mujoco``) and
    nothing here comes near it.

    Its own editor since ADR-108, and of the four it is the one that most
    wants to be left open in a corner: a run takes an hour and what you do
    with this panel is glance at it. ``docs/BLENDER-TREE.md`` 2a is still
    eight files -- the editors are 2b, which is where additive rows against
    inherited Blender belong.
    """

    bl_space_type = 'CADEX_TRAINING'
    bl_region_type = 'WINDOW'
    bl_label = "Training"

    @classmethod
    def poll(cls, context):
        from . import cadex_training
        # One stat. A project with no run in flight sees the parameters
        # editor exactly as it was, which is the same bargain the other two
        # panels make.
        return cadex_training.read_progress(context.scene) is not None

    def draw(self, context):
        from . import cadex_training
        layout = self.layout
        report = cadex_training.read_progress(context.scene)
        if report is None:
            return

        state = str(report.get("state") or "")
        total = int(report.get("total") or 0)
        done = int(report.get("iteration") or -1) + 1

        row = layout.row()
        icon = {"training": 'PLAY', "starting": 'TIME',
                "done": 'CHECKMARK', "failed": 'ERROR'}.get(state, 'INFO')
        row.label(text=state.title() or "Unknown", icon=icon)
        label = str(report.get("label") or "")
        if label:
            sub = row.row()
            sub.enabled = False
            sub.label(text=label)

        if state == "failed":
            box = layout.box()
            box.alert = True
            box.label(text=str(report.get("error") or "no reason recorded"),
                      icon='ERROR')

        # The bar is the honest one: iterations done over iterations asked
        # for. It is not a claim about the reward, which may be going the
        # wrong way -- that is what the two numbers below it are for.
        layout.progress(
            factor=(min(max(done / total, 0.0), 1.0) if total > 0 else 0.0),
            text="{:d} / {:d} iterations".format(done, max(total, 0)),
        )

        column = layout.column(align=True)
        column.enabled = False
        reward = report.get("reward_per_step")
        best = report.get("best_reward_per_step")
        column.label(
            text="reward/step  {:s}".format(
                "{:+.6g}".format(float(reward)) if reward is not None else "-"
            )
        )
        # Best-so-far and *where*, because the gap between it and the
        # current iteration is the whole decision this panel exists to
        # inform: a best that stopped moving a thousand iterations ago is a
        # run to stop.
        column.label(
            text="best         {:s}  at iteration {:d}".format(
                "{:+.6g}".format(float(best)) if best is not None else "-",
                int(report.get("best_iteration", -1)),
            )
        )
        # The row that would have caught ADR-101. Two runs reported a rising
        # reward while the policy got worse at the task, and the shape of it
        # is only visible here: an episode length that falls while the reward
        # climbs is a policy failing sooner and being paid more for it.
        # Read with `.get`, so a report written before ADR-101 draws a dash
        # rather than raising in a panel.
        steps = report.get("episode_steps")
        column.label(
            text="episode      {:s} steps".format(
                "{:.1f}".format(float(steps)) if steps is not None else "-"
            )
        )
        column.label(
            text="elapsed      {:s}".format(
                cadex_training.format_eta(report.get("wall_time_s"))
            )
        )
        if state in cadex_training.LIVE_STATES:
            column.label(
                text="remaining    {:s}".format(
                    cadex_training.format_eta(report.get("eta_s"))
                )
            )
        column.label(text="device       {:s}".format(
            str(report.get("device") or "-")))

        checkpoints = list(report.get("checkpoints") or ())
        if not checkpoints:
            return
        box = layout.box()
        box.label(text="Checkpoints pulled ({:d})".format(len(checkpoints)),
                  icon='FILE_BLANK')
        inner = box.column(align=True)
        inner.enabled = False
        # Newest first, and capped: a 2000-iteration run at every hundred is
        # twenty rows, but nothing stops somebody asking for every ten.
        for entry in list(reversed(checkpoints))[:8]:
            entry = dict(entry or {})
            value = entry.get("reward_per_step")
            inner.label(text="{:s}   {:s}".format(
                str(entry.get("path") or "?"),
                "{:+.6g}".format(float(value)) if value is not None else "-",
            ))
        if len(checkpoints) > 8:
            inner.label(text="...and {:d} more".format(len(checkpoints) - 8))

        # Where they are, said once, because a digest pasted from the wrong
        # directory is the failure this whole path exists to avoid.
        note = layout.row()
        note.enabled = False
        note.label(text="in the project folder, beside " +
                        cadex_training.PROGRESS_NAME)


class CADEX_PARAMS_PT_parameters(Panel):
    """The sole occupant of the parameters editor, and now literally so.

    It carried four other panel groups until ADR-108 gave each of them an
    editor of its own.
    """

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

        # The model selector is in the editor's header (spaces.py) -- it is a
        # setting, and the header is where an editor's chrome belongs. Every
        # *action*, the two pin gestures included, is in one row under the
        # message box (draw_chat_buttons).
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
    """Every control the chat has, in one row of four groups.

    They used to be in two places -- the pins in the header, everything else
    here -- which meant the answer to "where is the button" was "it depends".
    Now the header carries status and this row carries actions, grouped by
    what they act on rather than by what they look like:

    ``[attach paste pin-face pin-point define-terminal edit-path confirm-path
    cancel-path]`` gather things the *next message* will carry; ``[rebuild]`` acts on the *model*;
    ``[params script wiring]`` open and close *views*, each depressed while
    its view is open; ``[new-chat send]`` are the *turn*.

    Nothing in here is hidden when it does not apply. A row that changes width
    as you enter and leave Edit Mode moves every other button under the
    pointer, so ``Define Terminal`` greys out instead (ADR-067's gesture only
    exists on a mesh in Edit Mode). This panel has no ``poll`` for the same
    reason, and a test pins that.
    """
    from . import spaces
    from . import cadex_pick
    from . import cadex_terminal_pick
    from . import cadex_wire_path
    from . import wiring_ui

    agent = agent_module.get_agent()

    # --- what the next message will carry ---------------------------------
    gather = layout.row(align=True)
    pending = agent.pending_attachment_count()
    gather.operator(MESH_AGENT_OT_attach_image.bl_idname, icon='FILE_IMAGE',
                    text="{:d}".format(pending) if pending else "")
    gather.operator(MESH_AGENT_OT_paste_image.bl_idname, text="",
                    icon='PASTEDOWN')
    # Two pin gestures, one queue: a face pin names a BREP face the engine can
    # re-find, a point pin is a place and a direction, which is the only thing
    # an imported mesh can offer and exactly what a part.cable port is. By
    # string idname, because `cadex_pick` builds its classes lazily at
    # register time and there is no attribute here to reach for.
    pinned = cadex_pick.pending_pin_count()
    gather.operator("mesh_agent.pick_pin", icon='EYEDROPPER',
                    text="{:d}".format(pinned) if pinned else "")
    gather.operator("mesh_agent.pick_point", icon='CURSOR', text="")
    # Measuring a terminal off the model (ADR-067): the same kind of thing --
    # gathered now, read by the assistant on the next turn -- and counted the
    # same way, so several picks visibly batch into one message.
    terminal = gather.row(align=True)
    terminal.enabled = bool(
        cadex_terminal_pick.MESH_AGENT_OT_define_terminal.poll(context))
    queued = cadex_terminal_pick.pending_terminal_count()
    terminal.operator(
        cadex_terminal_pick.MESH_AGENT_OT_define_terminal.bl_idname,
        icon='SNAP_MIDPOINT',
        text="{:d}".format(queued) if queued else "")
    # Dragging a routed wire onto the path you wanted (ADR-118). Three states
    # and therefore three buttons: open the curve, send it, throw it away.
    # Cancel is an operator rather than "delete the object yourself", because
    # a state you reach by knowing which object to delete is not a state the
    # UI has. All three are drawn always and greyed when they do not apply,
    # for the reason this row exists.
    for operator, icon in (
        (cadex_wire_path.MESH_AGENT_OT_edit_wire_path, 'PARTICLE_PATH'),
        (cadex_wire_path.MESH_AGENT_OT_confirm_wire_path, 'CHECKMARK'),
        (cadex_wire_path.MESH_AGENT_OT_cancel_wire_path, 'X'),
    ):
        entry = gather.row(align=True)
        entry.enabled = bool(operator.poll(context))
        entry.operator(operator.bl_idname, icon=icon, text="")

    # --- act on the model --------------------------------------------------
    # Always here, always clickable while the assistant is idle: re-runs the
    # script the engine already holds and sends nothing, so it is the safe
    # thing to press when it is unclear which side is wrong (ADR-039). Not
    # "Rebuild From Saved Script", which pushes this file's buffer over the
    # engine -- wrong semantics for a button that is always on.
    layout.separator()
    layout.operator(MESH_AGENT_OT_rebuild_model.bl_idname, text="",
                    icon='FILE_REFRESH')

    # --- open and close views ---------------------------------------------
    # Depressed while open, so each button reads as the state as well as the
    # switch.
    views = layout.row(align=True)
    views.operator(MESH_AGENT_OT_toggle_params.bl_idname, text="",
                   icon='OPTIONS',
                   depress=params_area(context.screen) is not None)
    views.operator(spaces.MESH_AGENT_OT_show_script.bl_idname, text="",
                   icon='TEXT',
                   depress=spaces.script_area(context.screen) is not None)
    views.operator(wiring_ui.MESH_AGENT_OT_toggle_wiring.bl_idname, text="",
                   icon='NODETREE',
                   depress=wiring_ui.wiring_area(context.screen) is not None)
    # The collision overlay is not a view but reads as one here: on or off,
    # depressed while it is on -- the same one-button-reads-as-the-state
    # affordance (ADR-091).
    views.operator(MESH_AGENT_OT_toggle_collision.bl_idname, text="",
                   icon='MOD_PHYSICS',
                   depress=cadex_collision.SCENE_FLAG in context.scene)

    # --- the turn ----------------------------------------------------------
    # Starting over is one button, not a trash can: what the user wants back
    # is an assistant with an empty head, and that is the session as much as
    # the transcript (Agent.new_conversation).
    turn = layout.row(align=True)
    turn.operator(MESH_AGENT_OT_chat_new.bl_idname, text="", icon='FILE_NEW')
    if agent.busy:
        turn.operator(MESH_AGENT_OT_chat_cancel.bl_idname,
                      text="", icon='CANCEL')
    else:
        turn.operator(MESH_AGENT_OT_chat_send.bl_idname,
                      text="", icon='PLAY')


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
    MESH_AGENT_OT_toggle_collision,
    # Panel order IS registration order -- nothing here sets `bl_order` --
    # so these stay grouped by the editor they now live in (ADR-108).
    CADEX_ENV_PT_collision,
    CADEX_POLICY_PT_simulation,
    CADEX_POLICY_PT_actuators,
    CADEX_TRAINING_PT_training,
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
