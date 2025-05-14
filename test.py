# File: /c:/temp/mcp-samples/test.py

def replace_fields_in_format(file_path, fields_values):
    try:
        # Read the format string from the file
        with open(file_path, 'r') as file:
            format_string = file.read()
        result = format_string.format(**fields_values)
        return result
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except KeyError as e:
        print(f"Error: Missing key in fields_values: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Example usage
if __name__ == "__main__":
    txt_file_path = './prompts/sortDescription.txt'  # Path to the txt file
    fields_values = {
        'sortable_fields': 'example_value',  # Replace {fields}
        'another_field': 'another_value'  # Replace {another_field} if present
    }

    output = replace_fields_in_format(txt_file_path, fields_values)
    if output:
        print("Resulting string:")
        print(output)