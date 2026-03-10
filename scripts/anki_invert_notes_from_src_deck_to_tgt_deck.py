import json
import os
from datetime import datetime
import urllib.request
import urllib.error

# ==========================================
# Considerations and assumptions
# 
# AnkiConnect must be installed and enabled in Anki for this script to work.
# The script is designed to be run multiple times, and it will only copy
# source notes that have not been copied before, based on the presence of a tag.
#
# The script creates a backup of the source and target decks before making any changes,
# including the exact notes selected for copying and the payload sent to AnkiConnect.
#
# The script expects the source notes to have specific field names for front and back.
#
# The script allows duplicates when creating new notes to ensure all valid notes are created,
# even if Anki's duplicate detection would block some of them for some reason.
#
# The script saves a summary of each run, including how many notes were found, prepared, created, and tagged.
# ==========================================

# ==========================================
# Configuration
# ==========================================

# Local AnkiConnect API endpoint
ANKI_URL = "http://127.0.0.1:8765"

# Decks
# English: 🇦🇺
# Indonesian: 🇮🇩
# Kiswahili: 🇰🇪

# Name of the source deck
SOURCE_DECK = "🇦🇺"

# Name of the target deck
TARGET_DECK = "🇮🇩"

# Tag added to source notes after they are copied
SOURCE_TAG = "copied_source"

# Tag added to newly created inverted notes
TARGET_TAG = "copied_inverted"

# Field names used in the note type
FRONT_FIELD = "Front"
BACK_FIELD = "Back"

# Note type used when creating notes in the target deck
MODEL_NAME = "Basic"

# ==========================================
# Project paths
# ==========================================

# Directory where this script lives
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Project root (one level above scripts/)
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Backup folder inside the project
BACKUP_ROOT = os.path.join(PROJECT_ROOT, "backup")


# ==========================================
# AnkiConnect helper
# ==========================================

def invoke(action, **params):
    """
    Send a request to AnkiConnect and return the result.

    Parameters
    ----------
    action : str
        The AnkiConnect action name.
    params : dict
        Parameters passed to the action.

    Returns
    -------
    any
        The result returned by AnkiConnect.

    Raises
    ------
    RuntimeError
        If AnkiConnect is not reachable or returns an error.
    """
    payload = json.dumps({
        "action": action,
        "version": 6,
        "params": params
    }).encode("utf-8")

    request = urllib.request.Request(
        ANKI_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Could not connect to AnkiConnect. Make sure Anki is open "
            "and the AnkiConnect add-on is installed."
        ) from exc

    if data.get("error"):
        raise RuntimeError(data["error"])

    return data["result"]


# ==========================================
# File helpers
# ==========================================

def save_json(path, data):
    """
    Save Python data as a formatted JSON file.
    """
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def clean_tsv_value(value):
    """
    Convert a field value into a safe single-line TSV value.

    Tabs and line breaks are replaced so the TSV structure remains valid.
    """
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\t", " ")
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    return text


def export_notes_tsv(path, notes):
    """
    Export notes to a TSV file using the configured front/back field names.

    The first row is a header row.
    Each next row contains:
    Front<TAB>Back
    """
    with open(path, "w", encoding="utf-8") as file:
        file.write(f"{FRONT_FIELD}\t{BACK_FIELD}\n")

        for note in notes:
            fields = note.get("fields", {})

            front = fields.get(FRONT_FIELD, {}).get("value", "")
            back = fields.get(BACK_FIELD, {}).get("value", "")

            front = clean_tsv_value(front)
            back = clean_tsv_value(back)

            file.write(f"{front}\t{back}\n")


def make_backup_dir():
    """
    Create and return a timestamped backup directory.

    Returns
    -------
    tuple[str, str]
        (timestamp, absolute backup directory path)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = os.path.abspath(os.path.join(BACKUP_ROOT, timestamp))
    os.makedirs(backup_dir, exist_ok=True)
    return timestamp, backup_dir


# ==========================================
# Deck helpers
# ==========================================

def create_deck_if_missing(deck_name):
    """
    Create the deck if it does not already exist.
    """
    invoke("createDeck", deck=deck_name)


def find_note_ids_in_deck(deck_name):
    """
    Return all note IDs in the given deck.
    """
    return invoke("findNotes", query=f'deck:"{deck_name}"')


def get_notes_info(note_ids):
    """
    Return detailed information for the given note IDs.
    """
    if not note_ids:
        return []
    return invoke("notesInfo", notes=note_ids)


def get_all_deck_notes(deck_name):
    """
    Return all notes in a deck as:
    (note_ids, notes_info)
    """
    note_ids = find_note_ids_in_deck(deck_name)
    notes = get_notes_info(note_ids)
    return note_ids, notes


# ==========================================
# Backup logic
# ==========================================

def backup_current_state(backup_dir):
    """
    Backup both source and target decks before making any changes.

    Files created:
    - source_notes.json
    - target_notes.json
    - source.tsv
    - target.tsv
    """
    _, source_notes = get_all_deck_notes(SOURCE_DECK)
    _, target_notes = get_all_deck_notes(TARGET_DECK)

    save_json(os.path.join(backup_dir, "source_notes.json"), source_notes)
    save_json(os.path.join(backup_dir, "target_notes.json"), target_notes)

    export_notes_tsv(os.path.join(backup_dir, "source.tsv"), source_notes)
    export_notes_tsv(os.path.join(backup_dir, "target.tsv"), target_notes)


# ==========================================
# Copy logic
# ==========================================

def find_uncopied_source_note_ids():
    """
    Return source note IDs that do not have the source tag yet.

    This is what prevents repeated copying across runs.
    """
    query = f'deck:"{SOURCE_DECK}" -tag:{SOURCE_TAG} -tag:{TARGET_TAG}'
    return invoke("findNotes", query=query)


def prepare_inverted_notes(source_notes):
    """
    Build the payload for new inverted notes.

    For each valid source note:
    - new Front = original Back
    - new Back  = original Front

    Returns
    -------
    tuple[list[dict], list[int]]
        (new_notes_payload, valid_source_note_ids)

    valid_source_note_ids contains only the source note IDs that were
    successfully prepared, so they can be tagged later without mismatch.
    """
    new_notes = []
    valid_source_note_ids = []

    for note in source_notes:
        note_id = note.get("noteId")
        fields = note.get("fields", {})

        # Skip notes that do not contain the required fields
        if FRONT_FIELD not in fields or BACK_FIELD not in fields:
            print(f"Skipping note {note_id}: missing '{FRONT_FIELD}' or '{BACK_FIELD}'.")
            continue

        original_front = fields[FRONT_FIELD]["value"]
        original_back = fields[BACK_FIELD]["value"]

        if not str(original_front).strip() or not str(original_back).strip():
            print(f"Skipping note {note_id}: empty front or back.")
            continue

        new_notes.append({
            "deckName": TARGET_DECK,
            "modelName": MODEL_NAME,
            "fields": {
                FRONT_FIELD: original_back,
                BACK_FIELD: original_front,
            },
            "tags": [TARGET_TAG],
            "options": {
                "allowDuplicate": True # Allow duplicates because it's blocking the creation of inverted notes somehow, 
                                       # even when the content is different. 
                                       # This is a workaround to ensure all valid notes are created.
            }
        })

        valid_source_note_ids.append(note_id)

    return new_notes, valid_source_note_ids


def tag_successfully_copied_source_notes(source_note_ids, created_note_ids):
    """
    Add the source tag only to source notes whose corresponding target note
    was created successfully.

    Parameters
    ----------
    source_note_ids : list[int]
        Source note IDs that were actually prepared.
    created_note_ids : list[int | None]
        Result list returned by addNotes.

    Returns
    -------
    list[int]
        Source note IDs that were successfully tagged.
    """
    tagged_source_ids = []

    for source_id, created_id in zip(source_note_ids, created_note_ids):
        if created_id is not None:
            tagged_source_ids.append(source_id)

    if tagged_source_ids:
        invoke("addTags", notes=tagged_source_ids, tags=SOURCE_TAG)

    return tagged_source_ids


# ==========================================
# Main script
# ==========================================

def main():
    """
    Main workflow:

    1. Ensure the target deck exists.
    2. Create a timestamped backup folder.
    3. Save source/target deck backups as JSON and TSV.
    4. Find source notes that have not yet been copied.
    5. Prepare inverted notes.
    6. Save backup files for the selected notes and payload.
    7. Create notes in the target deck.
    8. Tag copied source notes.
    9. Save a run summary.
    """
    # Ensure the target deck exists before any operation
    create_deck_if_missing(TARGET_DECK)

    # Create the backup folder for this run
    timestamp, backup_dir = make_backup_dir()

    # Backup the current state of both decks before changing anything
    backup_current_state(backup_dir)

    # Find only source notes that have not been copied before
    uncopied_source_note_ids = find_uncopied_source_note_ids()

    # If there is nothing new to copy, save a summary and exit
    if not uncopied_source_note_ids:
        summary = {
            "timestamp": timestamp,
            "source_deck": SOURCE_DECK,
            "target_deck": TARGET_DECK,
            "found_new_notes": 0,
            "prepared_notes": 0,
            "created_notes": 0,
            "tagged_source_notes": 0,
            "backup_dir": backup_dir
        }

        save_json(os.path.join(backup_dir, "selected_source_notes.json"), [])
        save_json(os.path.join(backup_dir, "copied_notes_payload.json"), [])
        save_json(os.path.join(backup_dir, "run_summary.json"), summary)

        print("No new notes to copy.")
        print(f"Backup stored in: {backup_dir}")
        return

    # Load full note details for the selected source notes
    selected_source_notes = get_notes_info(uncopied_source_note_ids)

    # Save the exact source notes selected for this run
    save_json(
        os.path.join(backup_dir, "selected_source_notes.json"),
        selected_source_notes
    )

    # Build the new inverted notes and keep only valid source note IDs
    new_notes, valid_source_note_ids = prepare_inverted_notes(selected_source_notes)

    # Save the exact payload that will be sent to the target deck
    save_json(
        os.path.join(backup_dir, "copied_notes_payload.json"),
        new_notes
    )

    # If no valid notes could be prepared, save summary and exit
    if not new_notes:
        summary = {
            "timestamp": timestamp,
            "source_deck": SOURCE_DECK,
            "target_deck": TARGET_DECK,
            "found_new_notes": len(uncopied_source_note_ids),
            "prepared_notes": 0,
            "created_notes": 0,
            "tagged_source_notes": 0,
        }

        save_json(os.path.join(backup_dir, "run_summary.json"), summary)

        print("Notes were found, but none could be prepared.")
        print(f"Backup stored in: {backup_dir}")
        return

    # Create the new inverted notes in the target deck
    created_note_ids = invoke("addNotes", notes=new_notes)

    # Tag only the source notes whose inverted copies were created successfully
    tagged_source_ids = tag_successfully_copied_source_notes(
        valid_source_note_ids,
        created_note_ids
    )

    # Save the final run summary
    summary = {
        "timestamp": timestamp,
        "source_deck": SOURCE_DECK,
        "target_deck": TARGET_DECK,
        "found_new_notes": len(uncopied_source_note_ids),
        "prepared_notes": len(new_notes),
        "created_notes": sum(note_id is not None for note_id in created_note_ids),
        "tagged_source_notes": len(tagged_source_ids),
    }

    save_json(os.path.join(backup_dir, "run_summary.json"), summary)

    # Print a short terminal summary
    print(f"Backup stored in: {backup_dir}")
    print(f"Source notes found: {len(uncopied_source_note_ids)}")
    print(f"Prepared notes: {len(new_notes)}")
    print(f"Created notes: {sum(note_id is not None for note_id in created_note_ids)}")
    print(f"Tagged source notes: {len(tagged_source_ids)}")


if __name__ == "__main__":
    main()