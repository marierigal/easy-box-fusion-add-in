# EasyBox — Autodesk Fusion Add-In

<p align="center"><a href="https://www.autodesk.fr/products/fusion-360"><img src="/docs/assets/autodesk-fusion-logo.svg" height="160" width="auto" alt="Autodesk Fusion 360" /></a></p>

EasyBox is an [Autodesk Fusion](https://www.autodesk.com/fr/products/fusion-360/overview) add-in that helps with creating boxes or other panel based projects.

## Features

###  Dress Up

> Design → Solid → Create → ![Dress Up Icon](/commands/dressUp/resources/16x16.png) Dress Up

Create panels from a solid

- Set a name for each panel
- Set the thickness of each panel
- Create a component for each panel (optional)
- Support user parameters

### Box Joint

> Design → Solid → Modify → ![Box Joint Icon](/commands/boxJoint/resources/16x16.png) Box Joint

Create box joints between two or more bodies

- Choose which body to cut the mortises into
- Choose which faces to create the tenons on
- Set the number of tenons
- Set the width of the tenons or use the auto width feature
- Add an *as built joint* between the bodies (optional)
- Remembers settings for the next operation
- Support user parameters

## Installation

1. Download the latest release from the releases page
2. Open Fusion
3. Click on `Scripts and Add-Ins...` button on the toolbar under the  `Utilities → Add-Ins` menu
4. Click on the `Add-Ins` tab
5. Click on the `+` icon
6. Select the downloaded file
7. Click `Run`, this adds:
   - `Dress Up` to the `Solid → Create` menu
   - `Box Joint` to the `Solid → Modify` menu

## Usage

### Step 1

Start by creating a solid box that is the size you want the final box to be. You can also create the box from a sketch by extruding it.

![Step 1 demo](/docs/assets/step1.gif)

### Step 2

Then, create panels from the solid box:

1. Click on the `Dress Up` button on the toolbar under the `Solid → Create` menu.
2. Select a face on the solid box, all faces will be selected by default (uncheck the `Select All` checkbox to disable this feature).
3. You can deselect faces you don't want to create a panel from by clicking on them.
4. Enter the thickness you want the panels of the box to be and click the `Apply Thickness` button to update all panels configuration.
5. You can set the name and the thickness of each panels by expanding the `Advanced Configuration` section.
6. When you are satisfied with the result, click the `OK` button.

![Step 2 demo](/docs/assets/step2.gif)

### Step 3

Add box joints:

1. Click on the `Box Joint` button on the toolbar under the `Solid → Modify` menu.
2. Select the body you want the mortises to be cut into.
3. Select all the faces that you want to create the tenons on.
4. Enter the number of tenons you want to create for each face.
5. Uncheck the `Auto Width` checkbox if you want to set the width of the tenons manually. Otherwise, the width will be calculated automatically to be equal to the mortises width.
6. When you are satisfied with the result, click the `OK` button.
7. Check the `Add Joint` checkbox if you want to add an *as built joint* between each pair of bodies.
8. Repeat the process for the other panels.

![Step 3 demo](/docs/assets/step3.gif)

### You're done!

You can modify the original solid box as you want, the panels and the joints will update automatically.

![Final demo](/docs/assets/final.gif)

## Development

You need to have [Visual Studio Code](https://code.visualstudio.com) installed on your machine to use the debugger with Fusion.

1. Clone the repository.
2. Move the folder into the Fusion add-ins folder:
   - MacOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns`
   - Windows: `%appdata%\Autodesk\Autodesk Fusion 360\API\AddIns`
3. Open Fusion.
4. Click on the `Scripts and Add-Ins...` button on the toolbar under the `Utilities → Add-Ins` menu.
5. Under the `Add-Ins` tab, click on the `BoxJoints` add-in.
6. Click on the `Debug` button, this will open the add-in in [Visual Studio Code](https://code.visualstudio.com).
7. Start the debugger by clicking on the `Run and Debug → Python Debugger: debug using launch.json` button on the toolbar.
8. Then select `Python: Attach launch.json` from the dropdown.
9. Make changes to the code and save the file, then reload the add-in in Fusion by clicking on the `Restart` button.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## References

- [autodesk Fusion documentation](https://help.autodesk.com/view/fusion360/ENU)

