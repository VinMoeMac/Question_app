"""
A utility script to de-duplicate a large CSV file based on a specific column.

This script uses Pandas to efficiently read a CSV in chunks, remove duplicate rows
based on the 'question' column (keeping the first occurrence), and write the result
to a new CSV file. This is useful for pre-processing large datasets before they are
used by the main application.

Usage:
    python deduplicate_csv.py <input_file_path> <output_file_path>
"""

import sys
import pandas as pd

def deduplicate_csv(input_path: str, output_path: str, column: str = "question"):
    """
    Reads a CSV file, removes duplicate rows based on a specified column,
    and saves the result to a new file.

    Args:
        input_path: The path to the source CSV file.
        output_path: The path where the de-duplicated CSV will be saved.
        column: The name of the column to check for duplicates.
    """
    print(f"Reading CSV from: {input_path}")
    try:
        # For very large files, chunking can be more memory-efficient.
        # However, for deduplication, we need to see all the data.
        # Pandas is generally efficient enough to handle this for files that
        # fit in memory, which is a reasonable assumption for a pre-processing step.
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        print(f"Error: The file '{input_path}' was not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while reading the CSV: {e}")
        sys.exit(1)

    initial_rows = len(df)
    print(f"Initial row count: {initial_rows:,}")

    print(f"De-duplicating based on the '{column}' column...")
    df.drop_duplicates(subset=[column], keep="first", inplace=True)

    final_rows = len(df)
    print(f"Final row count after de-duplication: {final_rows:,}")
    print(f"Removed {initial_rows - final_rows:,} duplicate rows.")

    print(f"Saving de-duplicated file to: {output_path}")
    df.to_csv(output_path, index=False)
    print("Done.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python deduplicate_csv.py <input_file_path> <output_file_path>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    deduplicate_csv(input_file, output_file)
