import adsk.core
import adsk.fusion
import os

from ...lib import fusionAddInUtils as futil
from ... import config

app = adsk.core.Application.get()
ui = app.userInterface
design = adsk.fusion.Design.cast(app.activeProduct)
default_units = design.unitsManager.defaultLengthUnits


CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_dressUp"
CMD_NAME = "Dress Up"
CMD_Description = "Offsets the walls of a solid body to create one panel per face. Select a body to dress up, remove unwanted faces, then specify the thickness of the panels."

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# This is done by specifying the workspace, the tab, and the panel, and the
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SolidCreatePanel"
COMMAND_BESIDE_ID = ""
IS_BEFORE = True

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "")

# Default thickness value
DEFAULT_THICKNESS = 0.3

# Input ids
SELECT_INPUT_ID = "select_input"
THICKNESS_INPUT_ID = "thickness_input"
TABLE_INPUT_ID = "table_input"

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

original_body: adsk.fusion.BRepBody = None


def add_header_row_to_table(table_input: adsk.core.TableCommandInput):
    table_inputs = table_input.commandInputs
    row_index = table_input.rowCount

    # Face ID
    face_id_header = table_inputs.addStringValueInput(
        "face_id_header", "Face ID Header", "ID"
    )
    face_id_header.isReadOnly = True
    table_input.addCommandInput(face_id_header, row_index, 0)

    # Panel name
    panel_name_header = table_inputs.addStringValueInput(
        "panel_name_header", "Panel Name Header", "Panel"
    )
    panel_name_header.isReadOnly = True
    table_input.addCommandInput(panel_name_header, row_index, 1)


def add_face_to_table(table_input: adsk.core.TableCommandInput, face_id: int):
    table_inputs = table_input.commandInputs
    row_index = table_input.rowCount

    # Add a string input for the face ID
    face_id_input = table_inputs.addStringValueInput(
        "face_{}".format(face_id),
        "Face ID",
        "{}".format(face_id),
    )
    face_id_input.isReadOnly = True
    table_input.addCommandInput(face_id_input, row_index, 0)

    # Add a string input for the panel name
    table_input.addCommandInput(
        table_inputs.addStringValueInput(
            "panel_name_{}".format(face_id),
            "Panel Name",
            "Panel {}".format(face_id),
        ),
        row_index,
        1,
    )


def on_body_selection(select_input: adsk.core.SelectionCommandInput):
    global original_body

    # Check if the selection is a body
    if (
        original_body
        or select_input.selectionCount == 0
        or select_input.selection(0).entity.objectType
        != adsk.fusion.BRepBody.classType()
    ):
        select_input.clearSelection()
        return

    # Get the table input
    table_input: adsk.core.TableCommandInput = select_input.commandInputs.itemById(
        TABLE_INPUT_ID
    )

    # Add all faces of the selected body to the faces input
    original_body = select_input.selection(0).entity

    # Update input to select faces
    select_input.clearSelection()
    select_input.tooltip = "Select the faces to dress up"
    select_input.clearSelectionFilter()
    select_input.addSelectionFilter("SolidFaces")
    select_input.setSelectionLimits(1, 0)

    for face in original_body.faces:
        select_input.addSelection(face)
        add_face_to_table(table_input, face.tempId)

    # Show the table input
    table_input.isVisible = True

    # Set the focus on the select input
    select_input.hasFocus = True


def on_faces_selection(select_input: adsk.core.SelectionCommandInput):
    table_input: adsk.core.TableCommandInput = select_input.commandInputs.itemById(
        TABLE_INPUT_ID
    )

    # NOTE: This is a workaround to clear the table (keeping the headers)
    #       as table_input.clear() seems to broke the app if called multiple times
    count = table_input.rowCount
    for _ in range(1, count):
        table_input.deleteRow(table_input.rowCount - 1)

    # Add all selected faces to the table
    for i in range(select_input.selectionCount):
        face: adsk.fusion.BRepFace = select_input.selection(i).entity
        add_face_to_table(table_input, face.tempId)


# Executed when add-in is run.
def start():
    # Create a command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER
    )
    cmd_def.toolClipFilename = ICON_FOLDER + "Toolclip.png"

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


# Executed when add-in is stopped.
def stop():
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


# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Created Event")

    # https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
    inputs = args.command.commandInputs

    # Create a selection input to select a body
    body_input = inputs.addSelectionInput(
        SELECT_INPUT_ID, "Select", "Select a body to dress up"
    )
    body_input.addSelectionFilter("SolidBodies")
    body_input.setSelectionLimits(1, 1)

    # Create a table input to display per faces configuration
    table_input = inputs.addTableCommandInput(
        TABLE_INPUT_ID, "Advanced Configuration", 2, "1:3"
    )
    table_input.maximumVisibleRows = 8
    add_header_row_to_table(table_input)
    # Create a value input to set the thickness value
    inputs.addValueInput(
        THICKNESS_INPUT_ID,
        "Thickness",
        default_units,
        adsk.core.ValueInput.createByReal(DEFAULT_THICKNESS),
    )

    # Create a table input to display per faces configuration
    table_input = inputs.addTableCommandInput(
        TABLE_INPUT_ID, "Advanced Configuration", 2, "1:3"
    )
    table_input.maximumVisibleRows = 8
    table_input.isVisible = False
    add_header_row_to_table(table_input)

    # Connect to the events of the command
    futil.add_handler(
        args.command.execute,
        command_execute,
        local_handlers=local_handlers,
    )
    futil.add_handler(
        args.command.inputChanged,
        command_input_changed,
        local_handlers=local_handlers,
    )
    futil.add_handler(
        args.command.executePreview,
        command_preview,
        local_handlers=local_handlers,
    )
    futil.add_handler(
        args.command.validateInputs,
        command_validate_input,
        local_handlers=local_handlers,
    )
    futil.add_handler(
        args.command.destroy,
        command_destroy,
        local_handlers=local_handlers,
    )


# This event handler is called when the user clicks the OK button in the command dialog or
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Execute Event")

    # Get a reference to your command's inputs.
    inputs = args.command.commandInputs

    select_input: adsk.core.SelectionCommandInput = inputs.itemById(SELECT_INPUT_ID)
    table_input: adsk.core.TableCommandInput = inputs.itemById(TABLE_INPUT_ID)

    faces = {}
    for i in range(select_input.selectionCount):
        face: adsk.fusion.BRepFace = select_input.selection(i).entity
        panel_name_input: adsk.core.StringValueCommandInput = (
            table_input.commandInputs.itemById(f"panel_name_{face.tempId}")
        )
        faces[panel_name_input.value] = face

    # Get body parent component
    parent_component = original_body.parentComponent

    for panel_name, face in faces.items():
        # Create a new component for the panel
        panel_occurence = parent_component.occurrences.addNewComponent(
            adsk.core.Matrix3D.create(),
        )
        panel_component = panel_occurence.component
        panel_component.name = panel_name

        # Create a new body for the panel
        thickness_input: adsk.core.ValueCommandInput = inputs.itemById(
            THICKNESS_INPUT_ID
        )
        panel_component.features.extrudeFeatures.addSimple(
            face,
            adsk.core.ValueInput.createByString(
                "{} * -1".format(thickness_input.expression)
            ),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        )

    # Remove the original body
    parent_component.features.removeFeatures.add(original_body)


# This event handler is called when the command needs to compute a new preview in the graphics window.
def command_preview(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Preview Event")
    inputs = args.command.commandInputs


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input

    # General logging for debug.
    futil.log(
        f"{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}"
    )

    if changed_input.id == SELECT_INPUT_ID:
        if original_body != None:
            # Handle the selection of faces
            on_faces_selection(changed_input)
        else:
            # Handle the selection of a body
            on_body_selection(changed_input)


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    # General logging for debug.
    futil.log(f"{CMD_NAME} Validate Input Event")

    inputs = args.inputs

    # Verify the validity of the input values. This controls if the OK button is enabled or not.
    thickness_input: adsk.core.ValueCommandInput = inputs.itemById(THICKNESS_INPUT_ID)
    if thickness_input.value <= 0:
        args.areInputsValid = False
        return

    args.areInputsValid = True


# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Destroy Event")

    global local_handlers, body_selected
    local_handlers = []
    body_selected = False
