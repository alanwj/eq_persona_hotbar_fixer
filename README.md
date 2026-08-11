# EQ Persona Hotbar Fixer

Separates your EverQuest persona hotbars from each other, preventing hotkey changes on one persona from affected others.

## How EQ Assigns Hotkeys

Global hotkeys are stored in `eqclient.ini`.

Persona specific hotkeys are stored in a file based on the character name, server, and class, following the pattern `CharacterName_server_CLS.ini`.

When using a persona, the EQ client assigns hotkeys first based on your persona specific file, and then falling back to the global file.

## The Problem

When you modify a hotkey, the EQ client saves the new key mapping to *both* the persona specific hotkeys *and* the global hotkeys.

This can break other personas in at least two ways:

1. If another persona is relying on a global hotkey, their mapping for that hotkey has now been (usually unintentionally) changed.

2. If another persona has never assigned that hotkey at all, the global hotkey now applies to the persona.

## How We Fix It

We fix the first problem by copying all of the global hotkeys into the persona specific hotkey file, isolating those hotkeys from other personas. We do not overwrite any hotkeys that are already assigned in the persona specific file.

We fix the second problem by explicitly marking globally unassigned hotkeys as unassigned in the persona specific file.

The end result is that changes to other persona hotkeys will no longer affect the "fixed" persona.