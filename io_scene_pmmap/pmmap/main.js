//TO-DO
//implement blender dropdowns for color baking

const fs = require('fs');
const path = require('path');
const pmmap = require('./pmmap');

let modelname = 'map';
let useColor = false;
let useBake = false;
let bakeSplit = false;
let skips = [];

/**
 * Processes the binary .d file.
 * @param {string} filePath - The path to the binary .d file.
 */
function processFile(filePath) {
    try {
        // Read the binary file as a buffer
        const buffer = fs.readFileSync(filePath);
        modelname = path.basename(filePath, path.extname(filePath));

        // Set variables as needed
        useColor = true;   // Example: enable color usage
        useBake = true;    // Example: enable baking
        bakeSplit = false; // Example: disable bake splitting
        skips = [];         // Example: no skips

        // Convert Buffer to ArrayBuffer
        const arrayBuffer = new Uint8Array(buffer).buffer;

        // Call loadEvent with the ArrayBuffer
        loadEvent({ result: arrayBuffer });
    } catch (error) {
        console.error("Error reading file:", error);
        // Optionally, you can also log the stack trace for more details
        console.error(error.stack);
        process.exit(1);
    }
}


/**
 * Handles the loaded data from the binary file.
 * @param {Object} event - An object containing the binary data.
 */
function loadEvent(event) {
    // Assuming pmmap.newArrayBufferSlice is adjusted for Node.js
    const arrayBufferSlice = pmmap.newArrayBufferSlice(event.result);
    const raw = pmmap.parse(arrayBufferSlice);

    if (raw && raw.information && raw.information.aNodeStr) {
        modelname = raw.information.aNodeStr;
    }

    let result = {};
    console.debug("Parsed Raw Data:", raw);

    // Call buildModel from pmmap.js
    pmmap.buildModel(raw);
    console.debug("Build Model Result:", result);

    // Draw the DAE using the updated model name
    drawDae(modelname);
}

/**
 * Generates and logs the DAE content.
 * @param {string} name - The name of the model.
 */

function drawDae(name) {
    if (bakeSplit) {
        name += '_bake_split';
    } else if (useBake) {
        name += '_bake';
    }

    console.log("Drawing DAE for model:", name);

    // Generate DAE content using pmmap.makeDae()
    const daeContent = pmmap.makeDae();

    // Determine the path to temp.txt in the parent directory
    const filePath = path.join(__dirname, '..', 'temp.txt');

    // Write daeContent to temp.txt
    fs.writeFile(filePath, daeContent, 'utf8', (err) => {
        if (err) {
            console.error("Error writing to temp.txt:", err);
        } else {
            console.log("DAE content successfully written to temp.txt in the parent directory");
        }
    });
}


// Execute processFile with the first command-line argument
async function main() {
    const args = process.argv.slice(2); // Get command-line arguments

    if (args.length < 1) {
        console.error('Usage: node main.js <binary_file_path>');
        process.exit(1); // Exit with failure
    }

    const binaryFilePath = args[0];
    processFile(binaryFilePath);
}

// Run the main function
main();
