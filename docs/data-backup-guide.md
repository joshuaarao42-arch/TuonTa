# Backing Up and Restoring Your TuonTa Library

TuonTa stores notes, decks, flashcards, review history, and quiz results in its local SQLite database. Export a backup before moving the library to another computer or making significant changes.

## Create a backup

1. Open TuonTa and locate the library export/transfer feature.
2. Export the library to a JSON file.
3. Save the exported file somewhere separate from the application folder, such as an external drive or a trusted cloud folder.
4. Keep an untouched copy of the export as your backup.

Avoid editing the JSON file manually. A malformed or incomplete export may not be importable.

## Restore or move a library

1. Install and open TuonTa on the destination computer.
2. Use the library import feature to select your exported JSON file.
3. Review the import summary before continuing your study session.
4. Confirm that your notes, decks, and cards appear as expected.

TuonTa's import operation is designed to be idempotent for matching library content: importing the same export again should not create duplicate notes, decks, and cards.

## Good backup habits

- Export regularly, especially after adding a large set of cards.
- Keep more than one backup and label copies with the date.
- Test an export by importing it into a separate or temporary library when practical.
- Do not share an export publicly if it contains private notes or personal study material.

A JSON export is a portable backup; it does not replace keeping a separate copy of the original database.
