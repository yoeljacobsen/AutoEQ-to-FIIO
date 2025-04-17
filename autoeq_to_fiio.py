import requests
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
import io
import re
import os
import urllib.parse
import sys
import argparse # Added for command-line arguments

# --- Configuration ---
INDEX_URL = "https://raw.githubusercontent.com/jaakkopasanen/AutoEq/master/results/INDEX.md"
BASE_RAW_URL = "https://raw.githubusercontent.com/jaakkopasanen/AutoEq/master/results/"
PARAMETRIC_EQ_FILENAME_TEMPLATE_TXT = "{} ParametricEQ.txt"
PARAMETRIC_EQ_FILENAME_CSV = "ParametricEQ.csv"
DEFAULT_DSP_MODEL = "FIIO KA17" # Default model for the XML output

# Cache file configuration
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".autoeq_fiio_converter_cache")
INDEX_CACHE_FILE = os.path.join(CACHE_DIR, "autoeq_index_cache.md")
ETAG_CACHE_FILE = os.path.join(CACHE_DIR, "autoeq_index_cache.etag")

# FiiO type mapping from Standard AutoEq Filter Names
FILTER_TYPE_MAP = {
    "Peaking": "0",
    "Low Shelf": "1",
    "High Shelf": "2",
}
# Mapping from Text Format Abbreviations to Standard Names
TEXT_FORMAT_TYPE_MAP = {
    "LSC": "Low Shelf",
    "HSC": "High Shelf",
    "PK": "Peaking",
}
# Regex for parsing the text filter format
TEXT_FILTER_REGEX = re.compile(
    r"Filter\s+\d+:"       # "Filter N:"
    r"\s+ON"               # " ON"
    r"\s+(\w+)"            # Filter type abbreviation (LSC, HSC, PK) - Group 1
    r"\s+Fc\s+([\d.]+)"    # " Fc FREQUENCY" - Group 2
    r"\s+Hz"               # " Hz"
    r"\s+Gain\s+([-\d.]+)" # " Gain GAIN" - Group 3
    r"\s+dB"               # " dB"
    r"\s+Q\s+([\d.]+)"     # " Q Q_VALUE" - Group 4
    , re.IGNORECASE
)

# --- Helper Functions ---

def fetch_index():
    """Fetches the AutoEq index file from GitHub, using local cache if possible."""
    # (No changes from v5)
    print("Checking for cached headphone index...")
    cached_etag = None
    headers = {}
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
    except OSError as e:
        print(f"Warning: Could not create cache directory {CACHE_DIR}: {e}. Caching disabled.")
    if os.path.exists(CACHE_DIR):
        try:
            if os.path.exists(ETAG_CACHE_FILE):
                with open(ETAG_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cached_etag = f.read().strip()
                if cached_etag:
                    headers['If-None-Match'] = cached_etag
                    # print(f"Found cached ETag: {cached_etag}") # Less verbose
        except IOError as e:
            print(f"Warning: Could not read ETag cache file {ETAG_CACHE_FILE}: {e}")
            cached_etag = None
    # print(f"Fetching headphone index from {INDEX_URL}...") # Less verbose
    try:
        response = requests.get(INDEX_URL, headers=headers, timeout=30)
        if response.status_code == 304:
            print("Remote index unchanged (304 Not Modified). Using cached version.")
            try:
                with open(INDEX_CACHE_FILE, 'r', encoding='utf-8') as f:
                    index_content = f.read()
                # print("Index loaded successfully from cache.") # Less verbose
                return index_content
            except IOError as e:
                print(f"Error: Could not read cached index file {INDEX_CACHE_FILE}: {e}")
                print("Attempting to fetch fresh index without ETag...")
                response = requests.get(INDEX_URL, timeout=30)
                response.raise_for_status()
        response.raise_for_status()
        index_content = response.text
        new_etag = response.headers.get('ETag')
        print("Fetched new index successfully.")
        if os.path.exists(CACHE_DIR):
            try:
                with open(INDEX_CACHE_FILE, 'w', encoding='utf-8') as f:
                    f.write(index_content)
                # print(f"Saved index content to cache: {INDEX_CACHE_FILE}") # Less verbose
                if new_etag:
                    with open(ETAG_CACHE_FILE, 'w', encoding='utf-8') as f:
                        f.write(new_etag)
                    # print(f"Saved new ETag to cache: {ETAG_CACHE_FILE}") # Less verbose
                elif os.path.exists(ETAG_CACHE_FILE):
                     os.remove(ETAG_CACHE_FILE)
            except IOError as e:
                print(f"Warning: Could not write to cache files in {CACHE_DIR}: {e}")
        return index_content
    except requests.exceptions.RequestException as e:
        print(f"Error fetching index: {e}")
        print("Attempting to use cached index as fallback...")
        if os.path.exists(INDEX_CACHE_FILE):
             try:
                with open(INDEX_CACHE_FILE, 'r', encoding='utf-8') as f:
                    index_content = f.read()
                print("Successfully loaded index from cache as fallback.")
                return index_content
             except IOError as e_read:
                 print(f"Error reading fallback cache file {INDEX_CACHE_FILE}: {e_read}")
                 return None
        else:
             print("No cached index available for fallback.")
             return None


def parse_index(index_content):
    """Parses the Markdown index file to extract headphone names and paths."""
    # (No changes from v5)
    headphones = {}
    pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    # print("Parsing index...") # Less verbose
    lines = index_content.splitlines()
    count = 0
    for line in lines:
        if line.strip().startswith(("*", "-")):
            match = pattern.search(line)
            if match:
                name = match.group(1).strip()
                relative_path = match.group(2).strip().lstrip('./').lstrip('/').rstrip('/') + '/'
                if relative_path:
                    headphones[name] = relative_path
                    count += 1
    print(f"Found {count} headphone profiles.")
    return headphones

def search_headphones(headphones, search_term):
    """Filters the headphone list based on a search term."""
    # (No changes from v5)
    matches = {
        name: path
        for name, path in headphones.items()
        if search_term.lower() in name.lower()
    }
    return matches

def select_headphone(matches):
    """Prompts the user to select a headphone from the matches."""
    # (No changes from v5)
    if not matches:
        print("No matches found.")
        return None, None
    print("\nMatching headphone profiles:")
    match_list = list(matches.items())
    for i, (name, _) in enumerate(match_list):
        print(f"{i + 1}: {name}")
    while True:
        try:
            choice = input(f"Select a profile number (1-{len(match_list)}): ")
            index = int(choice) - 1
            if 0 <= index < len(match_list):
                selected_name, selected_path = match_list[index]
                print(f"Selected: {selected_name}")
                return selected_name, selected_path
            else:
                print("Invalid choice. Please enter a number from the list.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except EOFError:
            print("\nSelection cancelled.")
            return None, None


def fetch_parametric_eq_data(headphone_path, selected_name):
    """Fetches the Parametric EQ file for the selected headphone."""
    # (No changes from v5)
    filename_txt = PARAMETRIC_EQ_FILENAME_TEMPLATE_TXT.format(selected_name)
    filename_csv = PARAMETRIC_EQ_FILENAME_CSV
    encoded_filename_txt = urllib.parse.quote(filename_txt)
    url_txt = f"{BASE_RAW_URL}{headphone_path}{encoded_filename_txt}"
    url_csv = f"{BASE_RAW_URL}{headphone_path}{filename_csv}"
    print(f"Attempting to fetch EQ data from: {url_txt}")
    try:
        response = requests.get(url_txt, timeout=30)
        response.raise_for_status()
        print("EQ data fetched successfully (found .txt version).")
        return response.text
    except requests.exceptions.RequestException as e:
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 404:
            # print(f"Info: '{filename_txt}' not found (404).") # Less verbose
            print(f"Attempting fallback fetch from: {url_csv}")
            try:
                response = requests.get(url_csv, timeout=30)
                response.raise_for_status()
                print("EQ data fetched successfully (found .csv fallback).")
                return response.text
            except requests.exceptions.RequestException as e_csv:
                print(f"Error fetching EQ data (fallback .csv): {e_csv}")
                if isinstance(e_csv, requests.exceptions.HTTPError) and e_csv.response.status_code == 404:
                     print(f"Info: Fallback '{filename_csv}' also not found (404).")
                return None
        else:
            print(f"Error fetching EQ data (.txt): {e}")
            return None

def parse_eq_data(eq_content):
    """Parses the EQ content (detecting format) into a list of EQ band dictionaries."""
    # (No changes from v5)
    if not eq_content: return None, None
    # print("Parsing EQ data...") # Less verbose
    eq_bands = []
    preamp = 0.0
    lines = eq_content.strip().splitlines()
    preamp_found = False
    for line in lines:
        if not preamp_found and "preamp:" in line.lower():
            try:
                preamp_str = line.split(":")[1].strip().split(" ")[0]
                preamp = float(preamp_str)
                print(f"Found Preamp value: {preamp} dB")
                preamp_found = True
            except (IndexError, ValueError):
                print(f"Could not parse preamp value from line: {line.strip()}")
    if not preamp_found:
        print("Info: Preamp line not found in the data. Using default 0.0 dB.")

    is_text_format = any(TEXT_FILTER_REGEX.search(line) for line in lines)
    if is_text_format:
        # print("Detected Text Filter format.") # Less verbose
        for i, line in enumerate(lines):
            match = TEXT_FILTER_REGEX.search(line)
            if match:
                try:
                    type_abbr = match.group(1).upper()
                    freq_str = match.group(2)
                    gain_str = match.group(3)
                    q_str = match.group(4)
                    standard_type_name = TEXT_FORMAT_TYPE_MAP.get(type_abbr)
                    if not standard_type_name:
                        print(f"Warning: Skipping band on line {i+1} with unknown text type abbreviation: {type_abbr}")
                        continue
                    fiio_type = FILTER_TYPE_MAP.get(standard_type_name)
                    if fiio_type is None:
                        print(f"Internal Warning: Could not map standard type '{standard_type_name}' to FiiO code.")
                        continue
                    band = {
                        "type": fiio_type,
                        "freq": str(int(float(freq_str))),
                        "gain": str(float(gain_str)),
                        "q": str(float(q_str)),
                    }
                    eq_bands.append(band)
                except ValueError as ve:
                    print(f"Warning: Skipping band on line {i+1} due to value conversion error: {ve} in line '{line.strip()}'")
                except IndexError:
                     print(f"Warning: Skipping band on line {i+1} due to parsing error (IndexError) in line '{line.strip()}'")
    else:
        # print("Assuming CSV format.") # Less verbose
        csvfile = io.StringIO(eq_content)
        try:
            try:
                dialect = csv.Sniffer().sniff(csvfile.read(2048))
                csvfile.seek(0)
            except csv.Error:
                # print("Warning: CSV dialect sniffing failed. Assuming standard comma delimiter.") # Less verbose
                dialect = 'excel'
                csvfile.seek(0)
            reader = csv.reader(csvfile, dialect)
            try:
                header = next(reader)
                expected_headers = ["Filter Type", "Freq", "Q", "Gain"]
                is_header = all(h.strip().lower() in [eh.strip().lower() for eh in header] for h in expected_headers) or \
                            any(col.isalpha() for col in header[:4])
                if not is_header:
                    # print("Warning: First row doesn't look like a standard header. Attempting to parse from start.") # Less verbose
                    csvfile.seek(0)
                    reader = csv.reader(csvfile, dialect)
                # else: print(f"Detected header: {header}") # Less verbose
            except StopIteration:
                print("Error: EQ file (CSV) seems empty.")
                return None, None
            for i, row in enumerate(reader):
                if not row or len(row) < 4: continue
                try:
                    filter_type_name = row[0].strip()
                    freq_str = row[1].strip()
                    q_str = row[2].strip()
                    gain_str = row[3].strip()
                    fiio_type = FILTER_TYPE_MAP.get(filter_type_name)
                    if fiio_type is None:
                        if filter_type_name.replace('.', '', 1).isdigit() and len(row) >= 3:
                             # print(f"Warning: Assuming 'Peaking' filter for row {i+1} starting with numeric value.") # Less verbose
                             fiio_type = FILTER_TYPE_MAP["Peaking"]
                             freq_str = row[0].strip()
                             q_str = row[1].strip()
                             gain_str = row[2].strip()
                        else:
                             print(f"Warning: Skipping band {i+1} with unknown filter type: {filter_type_name}")
                             continue
                    try:
                        band = {
                            "type": fiio_type,
                            "freq": str(int(float(freq_str))),
                            "gain": str(float(gain_str)),
                            "q": str(float(q_str)),
                        }
                        eq_bands.append(band)
                    except ValueError as ve:
                        print(f"Warning: Skipping band {i+1} due to value conversion error: {ve} in row {row}")
                        continue
                except IndexError:
                    print(f"Warning: Skipping incomplete row {i+1}: {row}")
                    continue
        except csv.Error as e:
            print(f"Error parsing CSV data: {e}")

    if not eq_bands:
        print("Error: No valid EQ bands found in the data after parsing.")
        return None, None
    # print(f"Successfully parsed {len(eq_bands)} EQ bands.") # Less verbose
    return eq_bands, preamp


# --- MODIFIED create_fiio_xml ---
def create_fiio_xml(eq_bands, style_name, preamp_value, dsp_model_name): # Added dsp_model_name argument
    """Creates the FiiO DSP XML structure as a string, using the provided preamp and model name."""
    print(f"Generating FiiO XML for model '{dsp_model_name}' with MasterGain = {preamp_value}...")
    # --- Use the passed dsp_model_name for the model attribute ---
    root = ET.Element("FiiO_DSP", model=dsp_model_name, version="0.0.1") # MODIFIED: Use dsp_model_name here
    module = ET.SubElement(root, "module", name="EQ")
    eq_group = ET.SubElement(module, "eqGroup")
    master_gain = ET.SubElement(eq_group, "param", name="masterGain")
    master_gain.text = str(preamp_value)
    eq_list = ET.SubElement(eq_group, "eqList")
    max_bands = 10
    if len(eq_bands) > max_bands:
        print(f"Warning: AutoEq profile has {len(eq_bands)} bands, limiting to {max_bands} for FiiO.")
        eq_bands = eq_bands[:max_bands]
    for i, band in enumerate(eq_bands):
        eq_element = ET.SubElement(eq_list, "eq", index=str(i))
        for param_name, param_value in band.items():
            param_element = ET.SubElement(eq_element, "param", name=param_name)
            param_element.text = param_value
    style_name_element = ET.SubElement(root, "styleName")
    style_name_element.text = style_name
    description_element = ET.SubElement(root, "description")
    description_element.text = "Converted from AutoEq"
    rough_string = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ", encoding="UTF-8").decode('utf-8')
    # print("XML generated successfully.") # Less verbose
    return pretty_xml

def save_xml(xml_content, default_filename="output.xml"):
    """Prompts the user for a filename and saves the XML content."""
    # (No changes from v5)
    while True:
        try:
            filename = input(f"Enter filename to save XML (default: {default_filename}): ")
            if not filename: filename = default_filename
            base_filename = os.path.basename(filename)
            if not re.match(r'^[\w\-. ]+$', base_filename):
                 print("Warning: Filename contains potentially invalid characters.")
            if not (filename.lower().endswith(".xml") or filename.lower().endswith(".txt")):
                 filename += ".xml"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(xml_content)
            print(f"Successfully saved FiiO EQ profile to: {filename}")
            return True
        except IOError as e:
            print(f"Error saving file: {e}")
        except EOFError:
            print("\nSave cancelled.")
            return False

# --- Main Execution ---
if __name__ == "__main__":
    # --- Set up Argument Parser ---
    parser = argparse.ArgumentParser(description="Convert AutoEq profiles to FiiO Control XML format.")
    parser.add_argument(
        "-m", "--dsp-model",
        default=DEFAULT_DSP_MODEL,
        help=f"Target DSP model name for the XML output (default: '{DEFAULT_DSP_MODEL}')"
    )
    args = parser.parse_args()
    # --- Use the parsed DSP model ---
    target_dsp_model = args.dsp_model

    print(f"--- AutoEq to FiiO Control Converter (v6 - Target DSP: {target_dsp_model}) ---")

    index_content = fetch_index()
    if not index_content:
        print("Failed to retrieve headphone index. Exiting.")
        sys.exit(1)

    all_headphones = parse_index(index_content)
    if not all_headphones:
        print("Could not parse any headphones from the index. Exiting.")
        sys.exit(1)

    while True:
        try:
            search_term = input("Enter search term for headphones (or leave blank to list all): ")
            matches = search_headphones(all_headphones, search_term or "")
            selected_name, selected_path = select_headphone(matches)
            if selected_path: break
            elif not matches and search_term: print(f"No results for '{search_term}'. Try again.")
            elif not matches and not search_term: print("No headphones found. Try a search term.")
            elif selected_name is None and selected_path is None: sys.exit(0)
        except EOFError: print("\nExiting."); sys.exit(0)

    eq_file_content = fetch_parametric_eq_data(selected_path, selected_name)
    if not eq_file_content:
        print("Could not retrieve EQ data for the selected profile. Exiting.")
        sys.exit(1)

    eq_bands, preamp_value = parse_eq_data(eq_file_content)
    if not eq_bands:
        print("Failed to parse EQ bands from the data. Exiting.")
        sys.exit(1)

    safe_style_name = re.sub(r'[<>:"/\\|?*]', '_', selected_name)
    safe_filename_base = re.sub(r'[<>:"/\\|?*]', '_', selected_name).replace(' ', '_')

    # --- Pass target_dsp_model to create_fiio_xml ---
    fiio_xml = create_fiio_xml(eq_bands, safe_style_name, preamp_value, target_dsp_model) # MODIFIED

    save_xml(fiio_xml, default_filename=f"{safe_filename_base}_{target_dsp_model.replace(' ','_')}.xml") # Include model in default filename

    print("--- Conversion Complete ---")

