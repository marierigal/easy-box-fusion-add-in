import adsk.core
import adsk.fusion
import os

from ...lib import fusionAddInUtils as futil
from ... import config

app = adsk.core.Application.get()
ui = app.userInterface

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
SELECT_FACES_INPUT_ID = f"{CMD_ID}_select_faces_input"
SELECT_ALL_FACES_INPUT_ID = f"{CMD_ID}_select_all_faces_input"
THICKNESS_INPUT_ID = f"{CMD_ID}_thickness_input"
APPLY_THICKNESS_BUTTON_ID = f"{CMD_ID}_apply_thickness_button"
TABLE_INPUT_ID = f"{CMD_ID}_config_input"
TABLE_PANEL_FACE_ID_INPUT_ID = f"{CMD_ID}_config_panel_face_id_input"
TABLE_PANEL_NAME_INPUT_ID = f"{CMD_ID}_config_panel_name_input"
TABLE_PANEL_THICKNESS_INPUT_ID = f"{CMD_ID}_config_panel_thickness_input"
CONFIG_GROUP_INPUT_ID = f"{CMD_ID}_config_group"
CREATE_COMPONENT_INPUT_ID = f"{CMD_ID}_create_component_input"

# Table parameters
TABLE_COLUMNS_COUNT = 3
TABLE_LAYOUT = "1:3:3"
TABLE_PANEL_FACE_ID_COLUMN = 0
TABLE_PANEL_NAME_INPUT_COLUMN = 1
TABLE_PANEL_THICKNESS_INPUT_COLUMN = 2

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []


class PanelConfig:
    """
    Configuration for a panel.
    """

    def __init__(
        self,
        face_id: int,
        panel_name: str = "",
        thickness_expression: str = "",
    ):
        self.face_id = face_id
        self.panel_name = panel_name
        self.thickness_expression = thickness_expression

    def __eq__(self, value: object) -> bool:
        return isinstance(value, PanelConfig) and value.face_id == self.face_id


def start():
    """
    Executed when add-in is run.
    """

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

    # Get the body from the first selected face
    select_faces_input: adsk.core.SelectionCommandInput = inputs.itemById(
        SELECT_FACES_INPUT_ID
    )
    body: adsk.fusion.BRepBody = select_faces_input.selection(0).entity.body

    # Get the panel configurations
    panel_configs = get_panel_configs_from_table(inputs.itemById(TABLE_INPUT_ID))

    # Get the create component value
    create_component_input: adsk.core.BoolValueCommandInput = inputs.itemById(
        CREATE_COMPONENT_INPUT_ID
    )
    create_component = create_component_input.value

    # Dress up the body
    dress_up(body, panel_configs, create_component, remove_body=True)


def command_preview(args: adsk.core.CommandEventArgs):
    """
    This event handler is called when the command
    needs to compute a new preview in the graphics window.
    """

    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Preview Event")
    inputs = args.command.commandInputs

    # Get the body from the first selected face
    select_faces_input: adsk.core.SelectionCommandInput = inputs.itemById(
        SELECT_FACES_INPUT_ID
    )
    body: adsk.fusion.BRepBody = select_faces_input.selection(0).entity.body

    # Reduce the body opacity to help visualize the panels
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.activateRootComponent()  # NOTE: This is a workaround to avoid the body opacity to be reset
    body.opacity = 0.4

    # Draw the pointers for the selected faces
    draw_all_faces_labels(design, inputs)


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

    if changed_input.id == SELECT_FACES_INPUT_ID and isinstance(
        changed_input, adsk.core.SelectionCommandInput
    ):
        # Get the table input
        table_input: adsk.core.TableCommandInput = inputs.itemById(TABLE_INPUT_ID)

        # Reset the table if no faces are selected
        if changed_input.selectionCount == 0:
            table_input.clear()
            return

        # Get the body of the first selected face
        body: adsk.fusion.BRepBody = changed_input.selection(0).entity.body

        # Get the select all faces input
        select_all_faces_input: adsk.core.BoolValueCommandInput = inputs.itemById(
            SELECT_ALL_FACES_INPUT_ID
        )

        # Select all faces if the input is checked
        if select_all_faces_input.value:
            changed_input.clearSelection()
            for face in body.faces:
                changed_input.addSelection(face)
                select_all_faces_input.value = False

        # Get the thickness value
        thickness_input: adsk.core.ValueCommandInput = inputs.itemById(
            THICKNESS_INPUT_ID
        )
        thickness_expression = thickness_input.expression

        # Get previous panel configurations
        panel_configs = get_panel_configs_from_table(table_input)

        # Reset the table
        table_input.clear()
        add_header_row_to_table(table_input)

        # Add the face rows
        for i in range(changed_input.selectionCount):
            face: adsk.fusion.BRepFace = changed_input.selection(i).entity
            face_id = face.tempId

            panel_config = panel_configs.get(face_id)
            add_config_row_to_table(
                table_input,
                (
                    panel_config
                    if panel_config
                    else PanelConfig(face_id, f"Panel {face_id}", thickness_expression)
                ),
            )

    elif changed_input.id == APPLY_THICKNESS_BUTTON_ID:
        # Get the table input
        table_input: adsk.core.TableCommandInput = inputs.itemById(TABLE_INPUT_ID)

        # Get the thickness value
        thickness_input: adsk.core.ValueCommandInput = inputs.itemById(
            THICKNESS_INPUT_ID
        )
        thickness_expression = thickness_input.expression

        # Get the panel configurations
        panel_configs = get_panel_configs_from_table(table_input)

        # Update the thickness of all panels
        for panel_config in panel_configs.values():
            panel_config.thickness_expression = thickness_expression

        # Reset the table
        table_input.clear()
        add_header_row_to_table(table_input)

        # Add the face rows
        for panel_config in panel_configs.values():
            add_config_row_to_table(table_input, panel_config)


def command_destroy(args: adsk.core.CommandEventArgs):
    """
    This event handler is called when the command terminates.
    """

    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Destroy Event")

    # Reset the global variables
    global local_handlers
    local_handlers = []


def command_pre_select(args: adsk.core.SelectionEventArgs):
    """
    This event handler is called when the user
    hover over an object in the graphics window.
    """

    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Pre-Select Event")

    active_input = args.activeInput
    selected_entity = args.selection.entity

    if active_input.id == SELECT_FACES_INPUT_ID and active_input.selectionCount > 0:
        first_selected_entity = active_input.selection(0).entity

        # Prevent selecting a face that is not from the same body
        if selected_entity.body != first_selected_entity.body:
            args.isSelectable = False


def create_inputs(inputs: adsk.core.CommandInputs):
    """
    Create the inputs for the command dialog.
    """

    # Get the default length units
    default_units = app.activeProduct.unitsManager.defaultLengthUnits

    # Create a selection input to select a body
    select_faces_input_prompt = "Select faces to dress up"
    select_faces_input = inputs.addSelectionInput(
        SELECT_FACES_INPUT_ID, "Select", select_faces_input_prompt
    )
    select_faces_input.addSelectionFilter("SolidFaces")
    select_faces_input.setSelectionLimits(1, 0)
    select_faces_input.tooltip = select_faces_input_prompt

    # Create a boolean input to select all faces
    select_all_faces_input = inputs.addBoolValueInput(
        SELECT_ALL_FACES_INPUT_ID, "Select All", True, "", True
    )
    select_all_faces_input.tooltip = "Select all faces of the body"

    # Create a value input to set the thickness value
    thickness_input = inputs.addValueInput(
        THICKNESS_INPUT_ID,
        "Thickness",
        default_units,
        adsk.core.ValueInput.createByReal(DEFAULT_THICKNESS),
    )
    thickness_input.minimumValue = 0.01
    thickness_input.tooltipDescription = "The default thickness of the panels"

    # Create a button to apply the thickness to all panels
    apply_thickness_button = inputs.addBoolValueInput(
        APPLY_THICKNESS_BUTTON_ID, "Apply Thickness", False
    )
    apply_thickness_button.isFullWidth = True
    apply_thickness_button.tooltip = "Apply the thickness to all panels"

    # Create a bool input to allow component creation
    create_component_input = inputs.addBoolValueInput(
        CREATE_COMPONENT_INPUT_ID, "Create Component", True, "", True
    )
    create_component_input.tooltip = "Create a component"
    create_component_input.tooltipDescription = (
        "If checked, a component will be created for each panel."
    )

    # Create an advanced configuration group
    config_group_input = inputs.addGroupCommandInput(
        CONFIG_GROUP_INPUT_ID,
        "Advanced Configuration",
    )
    config_group_input.isExpanded = False
    config_group_children = config_group_input.children

    # Create a table input to display per faces configuration
    table_input = config_group_children.addTableCommandInput(
        TABLE_INPUT_ID, "Panels", TABLE_COLUMNS_COUNT, TABLE_LAYOUT
    )
    table_input.maximumVisibleRows = 8
    add_header_row_to_table(table_input)


def connect_to_events(command: adsk.core.Command):
    """
    Connect to the events of the command.
    """

    futil.add_handler(command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(
        command.inputChanged, command_input_changed, local_handlers=local_handlers
    )
    futil.add_handler(
        command.executePreview, command_preview, local_handlers=local_handlers
    )
    futil.add_handler(command.destroy, command_destroy, local_handlers=local_handlers)
    futil.add_handler(
        command.preSelect, command_pre_select, local_handlers=local_handlers
    )


def add_header_row_to_table(table_input: adsk.core.TableCommandInput):
    """
    Add the header row to the table input.
    """

    table_inputs = table_input.commandInputs
    row_index = table_input.rowCount

    # Face ID
    panel_name_header = table_inputs.addStringValueInput(
        f"_{TABLE_PANEL_FACE_ID_INPUT_ID}", "Face ID Header", "ID"
    )
    panel_name_header.isReadOnly = True
    table_input.addCommandInput(
        panel_name_header, row_index, TABLE_PANEL_FACE_ID_COLUMN
    )

    # Panel name
    panel_name_header = table_inputs.addStringValueInput(
        f"_{TABLE_PANEL_NAME_INPUT_ID}", "Panel Name Header", "Panel"
    )
    panel_name_header.isReadOnly = True
    table_input.addCommandInput(
        panel_name_header, row_index, TABLE_PANEL_NAME_INPUT_COLUMN
    )

    # Panel thickness
    panel_thickness_header = table_inputs.addStringValueInput(
        f"_{TABLE_PANEL_THICKNESS_INPUT_ID}", "Panel Thickness Header", "Thickness"
    )
    panel_thickness_header.isReadOnly = True
    table_input.addCommandInput(
        panel_thickness_header, row_index, TABLE_PANEL_THICKNESS_INPUT_COLUMN
    )


def add_config_row_to_table(
    table_input: adsk.core.TableCommandInput, panelConfig: PanelConfig
):
    """
    Add a face row to the table input.
    """

    table_inputs = table_input.commandInputs
    row_index = table_input.rowCount
    face_id = panelConfig.face_id

    # Add a readonly string input for the face id
    face_id_input = table_inputs.addStringValueInput(
        f"{TABLE_PANEL_FACE_ID_INPUT_ID}_{face_id}",
        "ID",
        str(face_id),
    )
    face_id_input.isReadOnly = True
    table_input.addCommandInput(face_id_input, row_index, TABLE_PANEL_FACE_ID_COLUMN)

    # Add a string input for the name of the panel
    panel_name_input = table_inputs.addStringValueInput(
        f"{TABLE_PANEL_NAME_INPUT_ID}_{face_id}",
        "Panel Name",
        panelConfig.panel_name,
    )
    table_input.addCommandInput(
        panel_name_input, row_index, TABLE_PANEL_NAME_INPUT_COLUMN
    )

    # Add a value input for the thickness of the panel
    panel_thickness_input = table_inputs.addValueInput(
        f"{TABLE_PANEL_THICKNESS_INPUT_ID}_{face_id}",
        "Thickness",
        app.activeProduct.unitsManager.defaultLengthUnits,
        adsk.core.ValueInput.createByString(panelConfig.thickness_expression),
    )
    table_input.addCommandInput(
        panel_thickness_input, row_index, TABLE_PANEL_THICKNESS_INPUT_COLUMN
    )


def get_panel_configs_from_table(
    table_input: adsk.core.TableCommandInput,
) -> dict:
    """
    Get the panel configurations from the table input.
    """

    panel_configs = {}
    for i in range(1, table_input.rowCount):
        face_id_input = table_input.getInputAtPosition(i, TABLE_PANEL_FACE_ID_COLUMN)
        face_id = int(face_id_input.value)
        name = table_input.getInputAtPosition(i, TABLE_PANEL_NAME_INPUT_COLUMN).value
        thickness = table_input.getInputAtPosition(
            i, TABLE_PANEL_THICKNESS_INPUT_COLUMN
        ).expression
        panel_configs[face_id] = PanelConfig(face_id, name, thickness)

    return panel_configs


def draw_face_label(
    face: adsk.fusion.BRepFace,
    graphics: adsk.fusion.CustomGraphicsGroup,
    config: PanelConfig,
):
    point = face.pointOnFace.copy()
    _, normal = face.evaluator.getNormalAtPoint(point)
    point.translateBy(normal)
    matrix = adsk.core.Matrix3D.create()
    matrix.translation = point.asVector()

    text = graphics.addText(config.panel_name, "Arial", 2, matrix)
    text.viewScale = adsk.fusion.CustomGraphicsViewScale.create(
        10, adsk.core.Point3D.create(0, 0, 0)
    )


def draw_all_faces_labels(
    design: adsk.fusion.Design,
    inputs: adsk.core.CommandInputs,
):
    """
    Daw a cone for each face in the table and highlight the selected face.
    """

    # Get the graphics group
    graphics_groups = design.rootComponent.customGraphicsGroups
    if graphics_groups.count > 0:
        for i in range(graphics_groups.count):
            graphics_groups.item(i).deleteMe()
    graphics = graphics_groups.add()

    # Get the table input
    table_input: adsk.core.TableCommandInput = inputs.itemById(TABLE_INPUT_ID)

    # Get the body from the first selected face
    select_faces_input: adsk.core.SelectionCommandInput = inputs.itemById(
        SELECT_FACES_INPUT_ID
    )
    body: adsk.fusion.BRepBody = select_faces_input.selection(0).entity.body

    panel_configs = get_panel_configs_from_table(table_input)

    for i in range(1, table_input.rowCount):
        face_id_input = table_input.getInputAtPosition(i, TABLE_PANEL_FACE_ID_COLUMN)
        face_id = int(face_id_input.value)
        face: adsk.fusion.BRepFace = body.findByTempId(face_id)[0]
        draw_face_label(face, graphics, panel_configs.get(face_id))


def dress_up(
    body: adsk.fusion.BRepBody,
    panel_configs: dict,
    create_component: bool = True,
    remove_body: bool = True,
):
    """
    Dress up a body with panels.
    """

    design = adsk.fusion.Design.cast(app.activeProduct)

    # Get the timeline marker position
    timeline = design.timeline
    start_index = timeline.markerPosition

    # Get body parent component
    parent_component = body.parentComponent

    for value in panel_configs.values():
        panel_config: PanelConfig = value

        if create_component:
            # Create a new component for the panel
            panel_occurence = parent_component.occurrences.addNewComponent(
                adsk.core.Matrix3D.create(),
            )
            panel_component = panel_occurence.component
            # Rename the component
            panel_component.name = panel_config.panel_name
        else:
            panel_component = parent_component

        # Create a new body for the panel
        value_input = adsk.core.ValueInput.createByString(
            f"{panel_config.thickness_expression} * -1"
        )
        extrude_feature = panel_component.features.extrudeFeatures.addSimple(
            body.findByTempId(panel_config.face_id)[0],
            value_input,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        )

        # Rename the extrude feature
        extrude_feature.name = f"Extrude ({panel_config.panel_name})"

        if not create_component:
            # Rename the body
            extrude_feature.bodies.item(0).name = panel_config.panel_name

    # Remove the body
    if remove_body:
        parent_component.features.removeFeatures.add(body)

    # Create a new timeline group
    group = timeline.timelineGroups.add(start_index, timeline.markerPosition - 1)
    group.name = f"Dress Up ({body.name})"
