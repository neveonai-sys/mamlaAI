#!/bin/bash

shopt -s extglob  # Enable extended pattern matching operators

# Traverse directories recursively
find draftdocs/ -depth -print0 | while IFS= read -r -d '' file; do
    dir=$(dirname "$file")       # Get directory path
    base=$(basename "$file")     # Get file or directory name

    # Remove leading dots
    newbase="${base#"${base%%[!.]*}"}"

    # Trim leading and trailing whitespace
    newbase="${newbase##+([[:space:]])}"  # Remove leading whitespace
    newbase="${newbase%%+([[:space:]])}"  # Remove trailing whitespace

    # Replace internal whitespace with '_'
    newbase="${newbase//+([[:space:]])/_}"

    # Delete special characters (keep letters, numbers, '.', '_', and '-')
    newbase=$(echo "$newbase" | tr -cd 'a-zA-Z0-9._-')

    # Reduce multiple dots to a single dot
    newbase=$(echo "$newbase" | sed 's/\.\{2,\}/./g')

    # Proceed if the name has changed
    if [ "$base" != "$newbase" ]; then
        newpath="$dir/$newbase"

        # Ensure the new path doesn't already exist
        if [ -e "$newpath" ]; then
            echo "Cannot rename '$file' to '$newpath': Target exists."
        else
            echo "Renaming '$file' to '$newpath'"
            mv "$file" "$newpath"
        fi
    fi
done

