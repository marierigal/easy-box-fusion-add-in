import adsk.core
import adsk.fusion
import platform
import os
import subprocess

from ...lib import fusionAddInUtils as futil
from ... import config

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_exportDXF"
CMD_NAME = "Export DXF"
CMD_Description = "Quickly export multiple faces profiles to DXF files."

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# This is done by specifying the workspace, the tab, and the panel, and the
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "UtilityPanel"
COMMAND_BESIDE_ID = ""
IS_BEFORE = True

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "")

# Input ids
SELECT_FACES_INPUT_ID = f"{CMD_ID}_select_faces_input"
FOLDER_INPUT_ID = f"{CMD_ID}_folder_input"
FOLDER_BUTTON_ID = f"{CMD_ID}_folder_button"

# Constants
SELECTION_SET_NAME = CMD_NAME
DEFAULT_EXPORT_FOLDER = os.path.join(os.path.expanduser("~"), "Desktop", "DXF")
MASTER_SKETCH_FILENAME = "master.dxf"
MASTER_SKETCH_MAX_X = 50
MASTER_SKETCH_SPACING = 0.1

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

export_folder = DEFAULT_EXPORT_FOLDER
folder_dialog: adsk.core.FolderDialog = None

master_sketch_offset_x, master_sketch_offset_y = 0, 0


def start():
    """
    Executed when add-in is run.
    """

    # Create a command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER
    )

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** Add a button into the UI so the user can run the command. ********
    # Get the target workspace the button will be created in.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    # Get the panel the button will be created in.
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    # Create the button command control in the UI after the specified existing command.
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, IS_BEFORE)

    # Specify if the command is promoted to the main toolbar.
    control.isPromoted = IS_PROMOTED


def stop():
    """
    Executed when add-in is stopped.
    """

    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    """
    Function that is called when a user clicks
    the corresponding button in the UI.
    This defines the contents of the command dialog
    and connects to the command related events.
    """

    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Created Event")

    # Create the inputs for the command dialog.
    create_inputs(args.command.commandInputs)

    # Connect to the command related events.
    connect_to_events(args.command)


def command_execute(args: adsk.core.CommandEventArgs):
    """
    This event handler is called when the user clicks
    the OK button in the command dialog or is immediately called
    after the created event not command inputs were created for the dialog.
    """

    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Execute Event")
    inputs = args.command.commandInputs

    design = adsk.fusion.Design.cast(app.activeProduct)

    # Get the selected faces
    select_faces_input: adsk.core.SelectionCommandInput = inputs.itemById(
        SELECT_FACES_INPUT_ID
    )
    selected_faces = [
        select_faces_input.selection(i).entity
        for i in range(select_faces_input.selectionCount)
    ]

    # Check if selection already exists
    selection_set = design.selectionSets.itemByName(SELECTION_SET_NAME)
    if selection_set:
        selection_set.deleteMe()

    # Save selection in a selection set
    selection_set = design.selectionSets.add(selected_faces, SELECTION_SET_NAME)

    # Check if folder exists, if not create it
    if not os.path.exists(export_folder):
        os.makedirs(export_folder)

    # Create a master sketch to copy the face sketches to
    master_sketch = design.rootComponent.sketches.add(
        design.rootComponent.xYConstructionPlane
    )
    master_sketch.isComputeDeferred = True

    # Export the faces to DXF files
    files: dict = {}
    for face in selected_faces:
        result, file_path = export_face_to_dxf(face, master_sketch)

        if result == True:
            files.update({file_path: result})
        else:
            futil.msg_box(
                f"Failed to export face to DXF: {file_path}",
                icon=adsk.core.MessageBoxIconTypes.CriticalIconType,
            )
            return

    # Export the master sketch to a DXF file
    master_sketch_filepath = os.path.join(export_folder, MASTER_SKETCH_FILENAME)
    master_sketch.saveAsDXF(master_sketch_filepath)

    # Delete the master sketch
    master_sketch.deleteMe()

    # Show a message box with the exported files
    message = f"<p>Exported {len(files)} faces to DXF files + 1 master:</b><ul>"
    for file in files.keys():
        message += f"<li><code>{file}</code></li>"
    message += f"<li><code>{master_sketch_filepath}</code></li></ul>"
    message += f"<p><i>Selection set added: {SELECTION_SET_NAME}</i></p>"
    message += f"<p><b>Do you want to open the export folder?</b></p>"

    result = futil.msg_box(
        message,
        buttons=adsk.core.MessageBoxButtonTypes.OKCancelButtonType,
        icon=adsk.core.MessageBoxIconTypes.InformationIconType,
    )

    if result == adsk.core.DialogResults.DialogOK:
        open_finder_at_folder(export_folder)


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    """
    This event handler is called when the user changes
    anything in the command dialog allowing you to modify
    values of other inputs based on that change.
    """

    changed_input = args.input
    inputs = args.inputs

    # General logging for debug.
    futil.log(
        f"{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}"
    )

    # Check if the folder button was clicked
    if changed_input.id == FOLDER_BUTTON_ID:
        # Show the folder dialog
        folder_dialog.showDialog()

        # Update the folder input
        folder_input: adsk.core.TextBoxCommandInput = inputs.itemById(FOLDER_INPUT_ID)
        folder_input.formattedText = folder_dialog.folder

        # Save the export folder
        global export_folder
        export_folder = folder_dialog.folder


def command_destroy(args: adsk.core.CommandEventArgs):
    """
    This event handler is called when the command terminates.
    """

    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Destroy Event")

    # Reset the global variables
    global local_handlers, folder_dialog, master_sketch_offset_x, master_sketch_offset_y
    local_handlers = []
    folder_dialog = None
    master_sketch_offset_x, master_sketch_offset_y = 0, 0


def create_inputs(inputs: adsk.core.CommandInputs):
    """
    Create the inputs for the command dialog.
    """

    # Create the selection input
    select_faces_input_tooltip = "Select the faces to export to DXF"
    select_faces_input = inputs.addSelectionInput(
        SELECT_FACES_INPUT_ID,
        "Select Faces",
        select_faces_input_tooltip,
    )
    select_faces_input.addSelectionFilter("SolidFaces")
    select_faces_input.setSelectionLimits(1, 0)
    select_faces_input.tooltip = select_faces_input_tooltip

    # Create the folder dialog
    global folder_dialog
    folder_dialog = ui.createFolderDialog()
    folder_dialog.title = "Select Export Folder"
    folder_dialog.initialDirectory = export_folder

    # Create the folder input
    folder_input = inputs.addTextBoxCommandInput(
        FOLDER_INPUT_ID, "Export Folder", export_folder, 2, True
    )

    # Create the folder button
    folder_button = inputs.addBoolValueInput(
        FOLDER_BUTTON_ID,
        "Browse",
        False,
    )
    folder_button.tooltip = "Select the folder to export the DXF files"
    folder_button.isFullWidth = True


def connect_to_events(command: adsk.core.Command):
    """
    Connect to the events of the command.
    """

    futil.add_handler(command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(
        command.inputChanged, command_input_changed, local_handlers=local_handlers
    )
    futil.add_handler(command.destroy, command_destroy, local_handlers=local_handlers)


def export_face_to_dxf(
    face: adsk.fusion.BRepFace, master: adsk.fusion.Sketch
) -> tuple[bool, str]:
    """
    Export the face to a DXF file.
    """

    global master_sketch_offset_x, master_sketch_offset_y

    try:
        # Get the root component
        design = adsk.fusion.Design.cast(app.activeProduct)
        root_component = design.rootComponent

        # Get the name of the face
        face_name = f"{face.body.name}-{face.tempId}"
        ancestors = root_component.allOccurrencesByComponent(face.body.parentComponent)
        for ancestor in ancestors:
            face_name = f"{ancestor.name}-{face_name}"
        face_name = face_name.replace(":", "_").replace(" ", "_")

        # Get the file path
        file_path = os.path.join(export_folder, f"{face_name}.dxf")

        # Create a sketch on the face
        sketch = root_component.sketches.add(face)

        # Project the face into the sketch
        sketch.project(face)

        # # Save the sketch as a DXF file
        sketch.saveAsDXF(file_path)

        # Redefine sketch plane to be root XY plane
        sketch.redefine(design.rootComponent.xYConstructionPlane)

        # Calculate sketch translation
        master_min = master.boundingBox.minPoint
        master_min.translateBy(
            adsk.core.Vector3D.create(master_sketch_offset_x, master_sketch_offset_y, 0)
        )
        sketch_min = sketch.boundingBox.minPoint
        trans_matrix = adsk.core.Matrix3D.create()
        trans_matrix.translation = sketch_min.vectorTo(master_min)

        # Copy the sketch curves to the master sketch
        obj_collection = adsk.core.ObjectCollection.create()
        for item in sketch.sketchCurves:
            obj_collection.add(item)
        sketch.copy(obj_collection, trans_matrix, master)

        # Update the master sketch offsets
        master_sketch_offset_x = master.boundingBox.maxPoint.x + MASTER_SKETCH_SPACING
        if master.boundingBox.maxPoint.x > MASTER_SKETCH_MAX_X:
            master_sketch_offset_x = 0
            master_sketch_offset_y = (
                master.boundingBox.maxPoint.y + MASTER_SKETCH_SPACING
            )

        # Delete the sketch
        sketch.deleteMe()

        return [True, file_path]
    except Exception as e:
        futil.log(f"Failed to export face to DXF: {e}")
        return [False, file_path]


def open_finder_at_folder(folder_path):
    # Ensure the path is absolute
    absolute_path = os.path.abspath(folder_path)
    os_name = platform.system()

    try:
        if os_name == "Windows":
            subprocess.run(["explorer", absolute_path], check=True)
        elif os_name == "Darwin":  # macos
            subprocess.run(["open", absolute_path], check=True)
    except subprocess.CalledProcessError as e:
        futil.log(f"Failed to open Finder: {e}")
