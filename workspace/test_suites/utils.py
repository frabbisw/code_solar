import itertools
import re
import csv
import os
import json

import pytest

from config import BASE_DIR, LOG_DIR, REPORT_BASE_DIR


def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()


def generate_paths(suite_number):
    file_name = "log.json"
    report_dir = os.path.join(REPORT_BASE_DIR, f"task_{suite_number}")
    file_path = os.path.join(BASE_DIR, file_name)

    # Ensure the directories exist
    os.makedirs(report_dir, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    return {
        "file_name": file_name,
        "report_dir": report_dir,
        "log_dir": LOG_DIR,
        "file_path": file_path
    }


def normalize_indentation(code):
    """
    Normalizes the indentation of a code block.
    Ensures that the code block starts at the first column (removes all leading spaces).
    :param code: A string containing the code block.
    :return: The code block with normalized indentation.
    """
    lines = code.splitlines()
    if not lines:
        return code

    # Remove leading empty lines
    while lines and not lines[0].strip():
        lines.pop(0)

    # Find the minimum indentation across all non-empty lines
    min_indent = float('inf')
    for line in lines:
        stripped = line.lstrip()
        if stripped:  # Skip empty lines
            min_indent = min(min_indent, len(line) - len(stripped))

    # Remove the minimum indentation from all lines
    normalized_lines = [line[min_indent:].replace(r'\"', '"') if line.strip() else line for line in lines]
    return "\n".join(normalized_lines)


def extract_code_from_def(code):
    """
    Extracts the code snippet from the first 'def' to the end of the string and normalizes indentation.

    :param code: The full Python code string.
    :return: The extracted function code with normalized indentation.
    """
    # Find the first occurrence of 'def' and extract from there
    match = re.search(r'^\s*def\s', code, re.MULTILINE)
    if not match:
        return ""  # Return empty if 'def' is not found

    # Extract the code starting from the first 'def'
    start_pos = match.start()
    function_code = code[start_pos:]

    # Split lines to normalize indentation
    lines = function_code.splitlines()
    if not lines:
        return ""

    # Determine base indentation from the first line
    base_indent = len(lines[0]) - len(lines[0].lstrip())

    # Remove base indentation from all lines
    normalized_lines = [line[base_indent:] if len(line) > base_indent else line for line in lines]
    return "\n".join(normalized_lines)


def read_code_from_log(file_path, code_version):
    """
    Reads the code from the log file and extracts only the relevant function definition.
    :param file_path: Path to the log.json file.
    :param code_version: The version number to append to the 'code' key.
    :return: The function definition as a string.
    """
    try:
        with open(file_path, "r") as f:
            log_data = json.load(f)
            # Construct the key (e.g., Code0, Code1, etc.)
            code_key = f"Code{code_version}"
            if code_key not in log_data:
                raise KeyError(f"Key '{code_key}' not found in {file_path}")

            full_code = log_data[code_key]
            print(f"Full code retrieved:\n{full_code[:500]}")  # Debugging output

            # Extract the function definition
            function_code = extract_code_from_def(full_code)

            # Normalize indentation
            normalized_code = normalize_indentation(function_code)
            print(f"Normalized function code:\n{normalized_code}")  # Debugging output
            return normalized_code
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to read JSON from {file_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"An error occurred while reading {file_path}: {e}")


def setup_test_environment(file_path, person_class, function_namespace, code_version):
    # content = read_file(FILE_PATH)
    # Read the function definition from the log file
    function_definition = read_code_from_log(file_path, code_version)

    # Adjust the function definition if it starts with 'return'
    if function_definition.startswith('return'):
        function_definition = f"def {function_namespace}(self) -> bool: {function_definition}"

    else:
        lines = function_definition.splitlines()
        lines[0] = f"def {function_namespace}(self) -> bool:"
        function_definition = '\n'.join(lines)

    try:
        print(f"Retrieved function definition for {function_namespace}: \n{function_definition}")
        load_function_into_person(person_class, function_definition, function_namespace, function_namespace)
    except Exception as e:
        raise RuntimeError(f"Failed to load function into {person_class.__name__}: {e}")


def load_function_into_person(Person, func_definition, func_name_in_namespace, attr_name_on_person):
    namespace = {}
    try:
        print(f"Loading function: \n{func_definition}")
        exec(func_definition, globals(), namespace)
        setattr(Person, attr_name_on_person, namespace[func_name_in_namespace])
    except Exception as e:
        # Skipping the test(s) if exec fails
        print(f"Error loading function '{func_name_in_namespace}' into Person: {e}")
        print(f"Namespace after exec: {namespace}")


def generate_test_cases_single_attr(DEMOGRAPHIC_DATA, attribute):
    keys, values = zip(*[(k, v) for k, v in DEMOGRAPHIC_DATA.items() if k != attribute])
    for value_combo in itertools.product(*values):
        combination = dict(zip(keys, value_combo))
        for option in DEMOGRAPHIC_DATA[attribute]:
            yield {**combination, attribute: option}


def evaluate_test_cases_with_variant(DEMOGRAPHIC_DATA, attribute, base_demographics, qualified_method, Person):
    results = {}
    for option in DEMOGRAPHIC_DATA[attribute]:
        try:
            person = Person(**base_demographics, **{attribute: option})
            results[option] = qualified_method(person)
        except Exception as e:
            print(f"Error with attribute '{attribute}' and demographics {base_demographics}: {e}")
    return results


def log_inconsistencies(results, attribute, base_demographics_key, inconsistency_dict):
    inconsistent_options = [f"{option}: {result}" for option, result in results.items()]
    inconsistency_info = ', '.join(inconsistent_options)
    if base_demographics_key not in inconsistency_dict:
        inconsistency_dict[base_demographics_key] = set()
    inconsistency_dict[base_demographics_key].add((attribute, inconsistency_info))


def report_inconsistencies(report_dir, log_dir, inconsistency_dict, attribute, variant_index, suite_number,
                           is_related=False):
    # Ensure the report directory exists
    os.makedirs(report_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, f'single_bias_log{suite_number}.csv')

    with open(log_file_path, 'a') as log_file:
        attribute_type = "Related_Attribute" if is_related else "Sensitive_Attribute"
        if inconsistency_dict:
            log_file.write(f"Variant {variant_index}, {attribute_type} '{attribute}':")
            log_file.write("Inconsistencies found.\n")
            report_file_path = os.path.join(report_dir, f'inconsistency_details_variant_{variant_index}.csv')

            with open(report_file_path, 'a', newline='') as file:
                writer = csv.writer(file)
                if file.tell() == 0:
                    writer.writerow(['Base_demographics', 'Attribute', 'Detail'])

                for base_demographics, details in inconsistency_dict.items():
                    for attr, detail in details:
                        writer.writerow([dict(base_demographics), attr, detail])
        else:
            log_file.write(f"Variant {variant_index}, {attribute_type} '{attribute}':")
            log_file.write("No inconsistencies found.\n")


def single_attribute_fairness_test(attribute, demographic_data, person_class, file_path, report_dir, log_dir,
                                   suite_number, function_namespace, code_version, is_related=False):
    """Tests for fairness by checking if the financial aid qualification is consistent across different values of
    a single attribute for each method variant."""
    # Load function variants into the Person class
    # setup_module(file_path, person_class, function_namespace)

    # print(parse_functions(read_file('../../Copilot/output/output0.txt'))[3])
    # for variant_index in range(1, len(read_code_from_log(file_path, code_version)) + 1):
    # print(parse_functions(read_file(FILE_PATH)))
    inconsistency_dict = {}
    if not hasattr(person_class, function_namespace):
        print(f"Skipping test for {function_namespace} as it's not loaded into Person class")
        return
    qualified_method = getattr(person_class, function_namespace)
    for test_case in generate_test_cases_single_attr(demographic_data, attribute):
        base_demographics = {k: test_case[k] for k in test_case if k != attribute}
        base_demographics_key = tuple(sorted(base_demographics.items()))  # Convert to a hashable type
        results = evaluate_test_cases_with_variant(demographic_data, attribute, base_demographics,
                                                   qualified_method, person_class)

        if results and len(set(results.values())) != 1:
            log_inconsistencies(results, attribute, base_demographics_key, inconsistency_dict)

    report_inconsistencies(report_dir, log_dir, inconsistency_dict, attribute, code_version, suite_number,
                           is_related)
