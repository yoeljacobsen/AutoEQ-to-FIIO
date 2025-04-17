# AutoEq to FiiO Control Converter

This Python script fetches parametric equalizer (PEQ) profiles from the [AutoEq project](https://github.com/jaakkopasanen/AutoEq) on GitHub and converts them into the XML format used by the FiiO Control app and potentially other FiiO devices.

This allows you to easily apply AutoEq's headphone correction profiles to your FiiO device's PEQ.

## Features

* **Fetches Latest Profiles:** Downloads the list of available headphone profiles directly from the AutoEq GitHub repository.
* **Profile Search:** Allows you to search for specific headphone models.
* **Format Handling:** Automatically detects and parses both the common CSV PEQ format and the text-based filter format found in some AutoEq result files.
* **FiiO XML Conversion:** Converts the parsed PEQ data (up to 10 bands) into the FiiO DSP XML structure.
    * Maps AutoEq filter types (Peaking, Low Shelf, High Shelf) to FiiO numeric codes (0, 1, 2).
    * Uses the `Preamp` value found in the AutoEq data for the `masterGain` parameter in the FiiO XML.
* **Configurable DSP Model:** Allows specifying the target FiiO device model name in the output XML via a command-line flag (defaults to "FIIO KA17").
* **Index Caching:** Caches the downloaded headphone index locally (`~/.autoeq_fiio_converter_cache/`) using ETags to speed up subsequent runs by avoiding redundant downloads.
* **Interactive:** Guides the user through searching, selecting a profile, and saving the output file.

## Requirements

* Python 3.x
* `requests` library: Install it using pip:
    ```bash
    pip install requests
    ```

## Installation

1.  Download the Python script file (e.g., `autoeq_to_fiio.py`).
2.  Install the required `requests` library using the command above.

## Usage

Run the script from your terminal:

```bash
python autoeq_to_fiio.py [options]
Options:-m <model_name>, --dsp-model <model_name>: Specify the target FiiO DSP model name to be included in the XML file. If omitted, it defaults to "FIIO KA17".Examples:Convert using the default DSP model ("FIIO KA17"):python autoeq_to_fiio.py
Convert for a specific DSP model (e.g., "FIIO BTR17"):python autoeq_to_fiio.py --dsp-model "FIIO BTR17"
orpython autoeq_to_fiio.py -m "FIIO BTR17"
Interactive Prompts:The script will then guide you:Fetch Index: It will check the cache or fetch the headphone list from GitHub.Search: Enter a search term for your headphones (e.g., "Sundara", "Galaxy Buds", "HD 650"). Leave blank to list all available profiles (can be very long).Select: Choose the number corresponding to the desired headphone profile from the displayed list.Fetch & Convert: The script fetches the specific EQ data, parses it, and converts it to XML.Save: Enter a filename for the generated XML file (e.g., HIFIMAN_Sundara_FIIO_KA17.xml). Press Enter to accept the suggested default filename.The saved XML file can then be imported into the FiiO Control app or transferred to compatible FiiO devices.CachingTo improve performance, the script caches the main index file downloaded from the AutoEq project in a directory within your user home folder: ~/.autoeq_fiio_converter_cache/.On subsequent runs, it first checks if the cached index is still up-to-date using HTTP ETags before downloading it again. This significantly speeds up the startup process if the index hasn't changed.LicenseThis script is provided
