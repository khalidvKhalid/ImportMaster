# STEP_Quick_Import.py
# STEP Quick Import — Import STEP(s) into ACTIVE design (no new tab/document)
#
# Author: Khalid
# License: Free to use and share. Attribution appreciated.
#
# Notes:
# - Part Design allows ONLY one component.
# - STEP files that contain assembly or multi-component data
#   MUST be imported in Hybrid or Assembly design types.
#
# UI:
#  - Adds ONLY to NavToolbar (viewport navigation bar)

import adsk.core
import adsk.fusion
import traceback
import os
import base64

app = adsk.core.Application.get()
ui = app.userInterface
handlers = []

CMD_ID   = "stepQuickImportCommand"
CMD_NAME = "STEP Quick Import"
CMD_DESC = "Import STEP into the active design (no new tab)."

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCE_FOLDER = "resources"

_ICON_16_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAATUlEQVR4nGNg"
    "GJ7gP8P///8ZGBgY/4eHh/8MDAwM/4cHB/8fHx//7e3t/2ZmZr8pKSmfR0dH"
    "/0lJSZ8dHR3/8QAAqVwQy5nJxN8AAAAASUVORK5CYII="
)
_ICON_32_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAnElEQVR4nO2W"
    "wQ2AMAxFv0pQqQmQmWQYgG0QfQKcQH8gQm9Q8kY0lQ0m0m0a3pJwGm7c0mY1"
    "gQpKp9mQ0h7gQmYw0mQh0m8wH1V0k3b0Yl9kqk8y0jQm+o2G5m6xgHk8m6w"
    "0mQh0m8wH1V0k3b0Yl9kqk8y0jQm+o2G5n8A2yWQx9kq2GAAAAAElFTkSuQmCC"
)

def ensure_dir(p):
    try:
        os.makedirs(p, exist_ok=True)
    except:
        pass

def resource_dir():
    rdir = os.path.join(THIS_DIR, RESOURCE_FOLDER)
    ensure_dir(rdir)
    return rdir

def write_icon_if_missing(path: str, b64_data: str):
    if os.path.isfile(path):
        return
    try:
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64_data))
    except:
        pass

def ensure_icons():
    rdir = resource_dir()
    write_icon_if_missing(os.path.join(rdir, "16x16.png"), _ICON_16_B64)
    write_icon_if_missing(os.path.join(rdir, "32x32.png"), _ICON_32_B64)

def get_design():
    return adsk.fusion.Design.cast(app.activeProduct)

def _safe_do_events():
    try:
        adsk.doEvents()
    except:
        pass

def _safe_fit():
    try:
        vp = app.activeViewport
        if vp:
            vp.fit()
    except:
        pass

def _sanitize_name(name: str) -> str:
    if not name:
        return "ImportedSTEP"
    bad = '<>:"/\\|?*'
    out = "".join(("_" if c in bad else c) for c in name).strip()
    return out if out else "ImportedSTEP"

def _get_design_intent(design: adsk.fusion.Design):
    try:
        intent = design.designIntent
        try:
            return intent, str(intent).split('.')[-1]
        except:
            return intent, "Unknown"
    except:
        return None, "Unknown"

class StepQuickImportExecute(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            design = get_design()
            if not design:
                ui.messageBox("No active Fusion design. Open or create a design first.", CMD_NAME)
                return

            intent, intent_name = _get_design_intent(design)

            dlg = ui.createFileDialog()
            dlg.isMultiSelectEnabled = True
            dlg.title = "Select STEP file(s)"
            dlg.filter = "STEP Files (*.step;*.stp)"
            dlg.filterIndex = 0

            if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
                return

            try:
                paths = list(dlg.filenames)
            except:
                paths = [dlg.filename]

            import_mgr = app.importManager
            root = design.rootComponent

            imported = 0
            failed = []

            PartType     = getattr(adsk.fusion.DesignIntentTypes, "PartDesignIntentType", None)
            HybridType   = getattr(adsk.fusion.DesignIntentTypes, "HybridDesignIntentType", None)
            AssemblyType = getattr(adsk.fusion.DesignIntentTypes, "AssemblyDesignIntentType", None)

            if intent is not None and AssemblyType and intent == AssemblyType:
                ui.messageBox(
                    "This document is set to Assembly design.\n\n"
                    "STEP Quick Import is intended for Part or Hybrid designs.\n"
                    "Open a Part or Hybrid design and try again.",
                    CMD_NAME
                )
                return

            is_part = (intent is not None and PartType and intent == PartType)

            for step_path in paths:
                try:
                    step_opts = import_mgr.createSTEPImportOptions(step_path)

                    if is_part:
                        import_mgr.importToTarget(step_opts, root)
                    else:
                        base = _sanitize_name(os.path.splitext(os.path.basename(step_path))[0])
                        occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
                        comp = occ.component
                        comp.name = base
                        import_mgr.importToTarget(step_opts, comp)

                    imported += 1
                    _safe_do_events()

                except:
                    failed.append(step_path)

            _safe_fit()

            if failed and is_part:
                ui.messageBox(
                    "STEP import failed due to Design Type.\n\n"
                    "This document is set to Part Design.\n"
                    "Part Designs can only contain one component and cannot\n"
                    "accept STEP files with assembly or multi-component data.\n\n"
                    "To fix this:\n"
                    "• Change Design Type to Hybrid (recommended)\n"
                    "• Or change Design Type to Assembly\n\n"
                    "Location:\n"
                    "Document Settings → Design Type → Hybrid / Assembly",
                    CMD_NAME
                )
                return

            if failed:
                ui.messageBox(
                    f"Design intent: {intent_name}\n\n"
                    f"Imported: {imported}\nFailed: {len(failed)}\n\n"
                    + "\n".join(failed),
                    CMD_NAME
                )
            else:
                ui.messageBox(
                    f"Design intent: {intent_name}\n\nImported: {imported}",
                    CMD_NAME
                )

        except:
            ui.messageBox("STEP import failed:\n\n" + traceback.format_exc(), CMD_NAME)

class StepQuickImportCreated(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        cmd = adsk.core.Command.cast(args.command)
        on_exec = StepQuickImportExecute()
        cmd.execute.add(on_exec)
        handlers.append(on_exec)

def _delete_existing_control(toolbar, control_id):
    try:
        c = toolbar.controls.itemById(control_id)
        if c:
            c.deleteMe()
    except:
        pass

def add_command_to_ui():
    ensure_icons()

    old_def = ui.commandDefinitions.itemById(CMD_ID)
    if old_def:
        old_def.deleteMe()

    cmdDef = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, CMD_NAME, CMD_DESC, resource_dir()
    )

    onCreated = StepQuickImportCreated()
    cmdDef.commandCreated.add(onCreated)
    handlers.append(onCreated)

    nav = ui.toolbars.itemById("NavToolbar")
    if nav:
        _delete_existing_control(nav, CMD_ID)
        nav.controls.addCommand(cmdDef)

def remove_command_from_ui():
    nav = ui.toolbars.itemById("NavToolbar")
    if nav:
        _delete_existing_control(nav, CMD_ID)

    d = ui.commandDefinitions.itemById(CMD_ID)
    if d:
        d.deleteMe()

def run(context):
    add_command_to_ui()

def stop(context):
    remove_command_from_ui()
    global handlers
    handlers = []
