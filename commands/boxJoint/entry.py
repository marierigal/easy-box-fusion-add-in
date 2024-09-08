import adsk.core
import adsk.fusion
import os

from ...lib import fusionAddInUtils as futil
from ... import config

app = adsk.core.Application.get()
ui = app.userInterface


CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_boxJoint"
CMD_NAME = "Box Joint"
CMD_Description = "Create box joints between bodies. Specify the number of tenons, their width, and if an as built joint should be added."

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# This is done by specifying the workspace, the tab, and the panel, and the
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = "FusionSolidEnvironment"
PANEL_ID = "SolidModifyPanel"
COMMAND_BESIDE_ID = ""
IS_BEFORE = True

# Default values for the command inputs
DEFAULT_TENON_COUNT = 3
DEFAULT_AUTO_WIDTH = True
DEFAULT_TENON_WIDTH = 0.5
DEFAULT_ADD_JOINT = False

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "")

# Input ids
SELECT_BODY_INPUT_ID = f"{CMD_ID}_select_body"
SELECT_FACE_INPUT_ID = f"{CMD_ID}_select_face"
TENON_COUNT_INPUT_ID = f"{CMD_ID}_tenon_count"
AUTO_WIDTH_INPUT_ID = f"{CMD_ID}_tenon_auto_width"
TENON_WIDTH_INPUT_ID = f"{CMD_ID}_tenon_width"
ADD_JOINT_INPUT_ID = f"{CMD_ID}_add_joint"
STATUS_INPUT_ID = f"{CMD_ID}_status"

# Status textbox
STATUS_HTML_PREFIX = "<hr/>"
STATUS_HTML_DEFAULT_MESSAGE = "<i>Select a body and a face to join</i>"
STATUS_HTML_ERROR_START = "<span style='color:#ff0000'>"
STATUS_HTML_ERROR_END = "</span>"
STATUS_HTML_SUCCESS_START = "<span style='color:#009900'>"
STATUS_HTML_SUCCESS_END = "</span>"
status_input: adsk.core.TextBoxCommandInput = None

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

last_tenon_count = DEFAULT_TENON_COUNT
last_auto_width = DEFAULT_AUTO_WIDTH
last_tenon_width = DEFAULT_TENON_WIDTH
last_add_joint = DEFAULT_ADD_JOINT


class StatusLevel:
    """
    The different levels of status messages
    """

    def __init__(self):
        pass

    Info = 0
    Success = 1
    Error = 2


def start():
    """
    Executed when the add-in is run.
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

    select_body_input: adsk.core.SelectionCommandInput = inputs.itemById(
        SELECT_BODY_INPUT_ID
    )
    select_face_input: adsk.core.SelectionCommandInput = inputs.itemById(
        SELECT_FACE_INPUT_ID
    )
    tenon_count_input: adsk.core.IntegerSpinnerCommandInput = inputs.itemById(
        TENON_COUNT_INPUT_ID
    )
    auto_width_input: adsk.core.BoolValueCommandInput = inputs.itemById(
        AUTO_WIDTH_INPUT_ID
    )
    tenon_width_input: adsk.core.ValueCommandInput = inputs.itemById(
        TENON_WIDTH_INPUT_ID
    )
    add_joint_input: adsk.core.BoolValueCommandInput = inputs.itemById(
        ADD_JOINT_INPUT_ID
    )

    for face_index in range(select_face_input.selectionCount):
        create_mortises_and_tenons(
            select_body_input.selection(0).entity,
            select_face_input.selection(face_index).entity,
            tenon_count_input.value,
            tenon_width_input.expression if not auto_width_input.value else None,
            add_joint_input.value,
        )


def command_preview(args: adsk.core.CommandEventArgs):
    """
    This event handler is called when the command
    needs to compute a new preview in the graphics window.
    """

    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Preview Event")
    inputs = args.command.commandInputs

    select_body_input: adsk.core.SelectionCommandInput = inputs.itemById(
        SELECT_BODY_INPUT_ID
    )
    select_face_input: adsk.core.SelectionCommandInput = inputs.itemById(
        SELECT_FACE_INPUT_ID
    )
    tenon_count_input: adsk.core.IntegerSpinnerCommandInput = inputs.itemById(
        TENON_COUNT_INPUT_ID
    )
    auto_width_input: adsk.core.BoolValueCommandInput = inputs.itemById(
        AUTO_WIDTH_INPUT_ID
    )
    tenon_width_input: adsk.core.ValueCommandInput = inputs.itemById(
        TENON_WIDTH_INPUT_ID
    )
    add_joint_input: adsk.core.BoolValueCommandInput = inputs.itemById(
        ADD_JOINT_INPUT_ID
    )

    # Reduce the body opacity to help visualize the joint
    select_body_input.selection(0).entity.opacity = 0.4

    results = {}
    for face_index in range(select_face_input.selectionCount):
        results[face_index] = create_mortises_and_tenons(
            select_body_input.selection(0).entity,
            select_face_input.selection(face_index).entity,
            tenon_count_input.value,
            tenon_width_input.expression if not auto_width_input.value else None,
            add_joint_input,
        )

    args.isValidResult = min(results.values())


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

    global last_tenon_count, last_tenon_width, last_auto_width, last_add_joint

    # Reset the status message
    update_status_message()

    # On tenon auto width change, show or hide tenon width input
    if changed_input.id == AUTO_WIDTH_INPUT_ID:
        tenon_width_input = inputs.itemById(TENON_WIDTH_INPUT_ID)
        tenon_width_input.isVisible = not changed_input.value
        # Reset to default value to prevent inputs from being invalid
        tenon_width_input.value = last_tenon_width

    # On select body change, focus on select face input
    elif changed_input.id == SELECT_BODY_INPUT_ID:
        inputs.itemById(SELECT_FACE_INPUT_ID).hasFocus = True

    # Keep last tenon_count value for next time
    elif changed_input.id == TENON_COUNT_INPUT_ID:
        last_tenon_count = changed_input.value

    # Keep last tenon_width value for next time
    elif changed_input.id == TENON_WIDTH_INPUT_ID:
        last_tenon_width = changed_input.value

    # Keep last auto_width value for next time
    elif changed_input.id == AUTO_WIDTH_INPUT_ID:
        last_auto_width = changed_input.value

    # Keep last add_joint value for next time
    elif changed_input.id == ADD_JOINT_INPUT_ID:
        last_add_joint = changed_input.value


def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    """
    This event handler is called when the user interacts
    with any of the inputs in the dialog which allows you
    to verify that all of the inputs are valid and enables
    the OK button.
    """

    # General logging for debug.
    futil.log(f"{CMD_NAME} Validate Input Event")

    inputs = args.inputs

    select_body_input: adsk.core.SelectionCommandInput = inputs.itemById(
        SELECT_BODY_INPUT_ID
    )
    select_face_input: adsk.core.SelectionCommandInput = inputs.itemById(
        SELECT_FACE_INPUT_ID
    )

    tenon_count_input: adsk.core.IntegerSpinnerCommandInput = inputs.itemById(
        TENON_COUNT_INPUT_ID
    )

    # The tenon count should be an odd number and should be a positive integer
    if tenon_count_input.value % 2 == 0:
        update_status_message(
            "Tenons count should be an odd integer", StatusLevel.Error
        )
        args.areInputsValid = False
        return

    if select_body_input.selectionCount < 1 or select_face_input.selectionCount < 1:
        args.areInputsValid = False
        return


def command_destroy(args: adsk.core.CommandEventArgs):
    """
    This event handler is called when the command terminates.
    """

    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Destroy Event")

    global local_handlers, status_input
    local_handlers = []

    # Reset the status message input
    status_input = None

    # Reset the selected body opacity
    select_body_input = args.command.commandInputs.itemById(SELECT_BODY_INPUT_ID)
    if select_body_input.selectionCount > 0:
        select_body_input.selection(0).entity.opacity = 1


def command_pre_select(args: adsk.core.SelectionEventArgs):
    """
    This event handler is called when the user
    hover over an object in the graphics window.
    """

    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Pre-Select Event")

    inputs = args.activeInput.commandInputs

    selected_entity = args.selection.entity

    if args.activeInput.id == SELECT_FACE_INPUT_ID:
        select_body_input = inputs.itemById(SELECT_BODY_INPUT_ID)

        if select_body_input.selectionCount == 0:
            return

        selected_body: adsk.fusion.BRepBody = select_body_input.selection(0).entity

        # Prevent selecting a face from the selected body
        if selected_entity.body == selected_body:
            args.isSelectable = False
            return

        # Prevent selecting a face that is not coplanar with the selected body faces
        selectable = False
        for body_face in selected_body.faces:
            if are_faces_coplanar([selected_entity, body_face]):
                selectable = True
                break
        args.isSelectable = selectable


def create_inputs(inputs: adsk.core.CommandInputs):
    """
    Create the inputs for the command dialog.
    """

    # Get the default length units
    default_units = app.activeProduct.unitsManager.defaultLengthUnits

    # Create a selection input to select the body to cut the mortise
    select_body_input_tooltip = "Select a body to cut the mortise."
    select_body_input = inputs.addSelectionInput(
        SELECT_BODY_INPUT_ID, "Body", select_body_input_tooltip
    )
    select_body_input.addSelectionFilter("SolidBodies")
    select_body_input.setSelectionLimits(1, 1)
    select_body_input.tooltip = select_body_input_tooltip
    select_body_input.toolClipFilename = ICON_FOLDER + "Board.png"

    # Create a selection input to select the face for the tenon
    select_body_input_tooltip = "Select a face for the tenon."
    select_face_input = inputs.addSelectionInput(
        SELECT_FACE_INPUT_ID, "Face", select_body_input_tooltip
    )
    select_face_input.addSelectionFilter("SolidFaces")
    select_face_input.setSelectionLimits(1, 0)
    select_face_input.tooltip = select_body_input_tooltip
    select_face_input.toolClipFilename = ICON_FOLDER + "Face.png"

    # Create a value input to set the number of tenons
    tenon_count_input = inputs.addIntegerSpinnerCommandInput(
        TENON_COUNT_INPUT_ID,
        "Tenons Count",
        1,
        99,
        2,
        last_tenon_count,
    )

    # Create a bool to set if the tenon width should be calculated or user defined
    auto_width_input = inputs.addBoolValueInput(
        AUTO_WIDTH_INPUT_ID,
        "Auto Width",
        True,
        "",
        last_auto_width,
    )
    auto_width_input.tooltip = "Tenons and mortises will have the same width"

    # Create a value input to set the width of the tenons
    tenon_width_input = inputs.addValueInput(
        TENON_WIDTH_INPUT_ID,
        "Tenons Width",
        default_units,
        adsk.core.ValueInput.createByReal(last_tenon_width),
    )
    tenon_width_input.tooltip = "Set the width of the tenons"
    tenon_width_input.minimumValue = 0.1
    tenon_width_input.isVisible = False

    # Create a bool to set if an as built joint should be added
    add_joint_input = inputs.addBoolValueInput(
        ADD_JOINT_INPUT_ID,
        "Add Joint",
        True,
        "",
        last_add_joint,
    )
    add_joint_input.tooltip = "Add an as built joint between the bodies"
    add_joint_input.tooltipDescription = (
        "The joint will be added between the selected body and the body of the selected face.<br/><br/>"
        "No joint will be added if the selected face as the same parent component as the selected body."
    )

    # Create a status message textbox
    global status_input
    status_input = inputs.addTextBoxCommandInput(STATUS_INPUT_ID, "", "", 4, True)
    update_status_message()


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
    futil.add_handler(
        command.validateInputs, command_validate_input, local_handlers=local_handlers
    )
    futil.add_handler(command.destroy, command_destroy, local_handlers=local_handlers)
    futil.add_handler(
        command.preSelect, command_pre_select, local_handlers=local_handlers
    )


def get_plane_from_face(face: adsk.fusion.BRepFace) -> adsk.core.Plane:
    """
    Get a plane from a face.
    """

    point = face.pointOnFace
    _, normal = face.evaluator.getNormalAtPoint(point)
    return adsk.core.Plane.create(point, normal)


def are_faces_coplanar(faces: list[adsk.fusion.BRepFace]) -> bool:
    """
    Check if a list of faces are coplanar.
    """

    plane = get_plane_from_face(faces[0])
    for face in faces[1:]:
        if not plane.isCoPlanarTo(get_plane_from_face(face)):
            return False
    return True


def update_status_message(
    message: str = STATUS_HTML_DEFAULT_MESSAGE,
    info_level: StatusLevel = StatusLevel.Info,
):
    """
    Update the message in status textbox.
    """

    global status_input

    prefix = STATUS_HTML_PREFIX
    if info_level == StatusLevel.Success:
        prefix += STATUS_HTML_SUCCESS_START
    elif info_level == StatusLevel.Error:
        prefix += STATUS_HTML_ERROR_START

    suffix = ""
    if info_level == StatusLevel.Success:
        suffix += STATUS_HTML_SUCCESS_END
    elif info_level == StatusLevel.Error:
        suffix += STATUS_HTML_ERROR_END

    status_input.formattedText = f"{prefix}{message}{suffix}"


def get_common_parent_component(
    design: adsk.fusion.Design, *components: adsk.fusion.Component
) -> adsk.fusion.Component:
    """
    Get the first common parent component of the given components.
    """
    common_parent = design.rootComponent

    while True:
        parent_component = common_parent

        for i in range(parent_component.allOccurrences.count):
            child_component = design.rootComponent.allOccurrences.item(i).component

            # if child component contains all the given components
            is_common_parent = True
            for component in components:
                if not child_component.allOccurrencesByComponent(component).count:
                    is_common_parent = False
                    break

            # then it is a common parent
            if is_common_parent:
                common_parent = child_component
                break

            # else, check the next child component
        # if no children then the root component is the common parent
        else:
            common_parent = parent_component
            break

    return common_parent


def create_mortises_and_tenons(
    body: adsk.fusion.BRepBody,
    face: adsk.fusion.BRepFace,
    tenon_count: int,
    tenon_width_expression: str = None,
    add_as_built_joint: bool = False,
) -> bool:
    """
    Create mortises and tenons between a body and a face.
    """

    design = adsk.fusion.Design.cast(app.activeProduct)

    # Get timeline current marker position
    timeline = design.timeline
    timeline_start_index = timeline.markerPosition

    # Define working component as the first common parent component
    root_component = get_common_parent_component(
        design, body.parentComponent, face.body.parentComponent
    )

    ######################################
    # Create the sketch
    ######################################

    # Create a sketch on the selected face
    sketch = root_component.sketches.add(face)

    # Project the edges of the face onto the sketch
    face_lines: list[adsk.fusion.SketchLine] = []
    for edge in face.edges:
        for entity in sketch.project(edge):
            if isinstance(entity, adsk.fusion.SketchLine):
                entity.isConstruction = True
                face_lines.append(entity)

    # Find the two longest lines
    longest_line = max(face_lines, key=lambda line: line.length)
    index_of_longest_line = face_lines.index(longest_line)
    longest_lines = [
        face_lines[index_of_longest_line],
        face_lines[index_of_longest_line + 2],
    ]

    # Add dimensions to the longest line
    longest_line_dimension = sketch.sketchDimensions.addDistanceDimension(
        longest_line.startSketchPoint,
        longest_line.endSketchPoint,
        adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
        adsk.core.Point3D.create(
            longest_line.startSketchPoint.geometry.x + 1,
            longest_line.startSketchPoint.geometry.y + 1,
            0,
        ),
        False,
    )

    # Set the full length of the tenons
    joint_full_length = longest_line_dimension.parameter.name

    # Create an arbitrary rectangle
    rectangle = sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        adsk.core.Point3D.create(0, 0, 0),
        adsk.core.Point3D.create(1, 1, 0),
    )

    # Make the rectangle square
    prev_line = None
    for line in rectangle:
        if prev_line:
            sketch.geometricConstraints.addPerpendicular(prev_line, line)
        prev_line = line

    # Make the rectangle centered on the first longest line
    midpoint_a = sketch.sketchPoints.add(adsk.core.Point3D.create(0, 0, 0))
    sketch.geometricConstraints.addMidPoint(midpoint_a, rectangle.item(0))
    sketch.geometricConstraints.addMidPoint(midpoint_a, longest_lines[0])

    # Make the rectangle centered on the opposite longest line
    midpoint_b = sketch.sketchPoints.add(adsk.core.Point3D.create(0, 0, 0))
    sketch.geometricConstraints.addMidPoint(midpoint_b, rectangle.item(2))
    sketch.geometricConstraints.addMidPoint(midpoint_b, longest_lines[1])

    # Set the width of each tenon
    if not tenon_width_expression:
        tenon_width_expression = f"{joint_full_length} / (2 * {tenon_count} + 1)"

    # Add dimensions to the rectangle
    dimension = sketch.sketchDimensions.addDistanceDimension(
        rectangle.item(0).startSketchPoint,
        rectangle.item(0).endSketchPoint,
        adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
        midpoint_a.geometry,
    )
    dimension.parameter.expression = tenon_width_expression

    if not sketch.isFullyConstrained:
        update_status_message("Sketch is not fully constrained", StatusLevel.Error)
        return False

    ######################################
    # Extrude the profile
    ######################################

    # Create the extrude feature
    extrude_features = root_component.features.extrudeFeatures
    extrude_input = extrude_features.createInput(
        sketch.profiles.item(1),
        adsk.fusion.FeatureOperations.CutFeatureOperation,
    )
    extrude_input.setOneSideExtent(
        adsk.fusion.ThroughAllExtentDefinition.create(),
        adsk.fusion.ExtentDirections.NegativeExtentDirection,
    )
    extrude_input.participantBodies = [body]
    extrude_feature = extrude_features.add(extrude_input)

    if not extrude_feature:
        update_status_message("Extrude feature failed", StatusLevel.Error)
        return False

    ######################################
    # Create a pattern from the extrusion
    ######################################

    # Only create a pattern if there are more than one tenon
    if tenon_count > 1:
        extrude_feature_component = extrude_feature.parentComponent

        pattern_input_entities = adsk.core.ObjectCollection.create()
        pattern_input_entities.add(extrude_feature)

        pattern_spacing = adsk.core.ValueInput.createByString(
            f"({joint_full_length} - {tenon_width_expression} * {tenon_count})"
            f"/ ({tenon_count} + 1)"
            f"+ {tenon_width_expression}"
        )

        pattern_features = extrude_feature_component.features.rectangularPatternFeatures
        pattern_input = pattern_features.createInput(
            pattern_input_entities,
            rectangle.item(0),
            adsk.core.ValueInput.createByReal(tenon_count),
            pattern_spacing,
            adsk.fusion.PatternDistanceType.SpacingPatternDistanceType,
        )
        pattern_input.isSymmetricInDirectionOne = True
        pattern_feature = pattern_features.add(pattern_input)

        if not pattern_feature:
            update_status_message("Pattern feature failed", StatusLevel.Error)
            return False

    ######################################
    # Combine the bodies
    ######################################

    target_body = face.body

    tools = adsk.core.ObjectCollection.create()
    tools.add(body)

    combine_features = root_component.features.combineFeatures
    combine_input = combine_features.createInput(target_body, tools)
    combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    combine_input.isKeepToolBodies = True
    combine_feature = combine_features.add(combine_input)

    if not combine_feature:
        update_status_message("Combine feature failed", StatusLevel.Error)
        return False

    ######################################
    # Add joint
    ######################################

    body_component = body.parentComponent
    face_component = face.body.parentComponent

    if add_as_built_joint and not body_component == face_component:
        body_occurrence = body_component.allOccurrences.itemByName(body.name)
        face_occurrence = face_component.allOccurrences.itemByName(face.body.name)

        joints = root_component.asBuiltJoints
        joint_input = joints.createInput(body_occurrence, face_occurrence, None)
        joint_input.setAsRigidJointMotion()
        joint = joints.add(joint_input)

        if not joint:
            update_status_message("Joint creation failed", StatusLevel.Error)
            return False

    ######################################
    # Group the features on the timeline
    ######################################

    timeline_group = timeline.timelineGroups.add(
        timeline_start_index, timeline.markerPosition - 1
    )
    timeline_group.name = f"Box Joint ({body.parentComponent.name}::{body.name})"

    update_status_message("Preview available", StatusLevel.Success)
    return True
