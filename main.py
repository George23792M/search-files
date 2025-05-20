import os #Import for operating system functions (eg. file path manipuliation)
from concurrent.futures import ThreadPoolExecutor, as_completed #Import to use multithreading
import re #Import the 're' module to use regular expression
from functools import lru_cache
from typing import Optional


CLASS_REGEX = re.compile(r"\b(?:public\s+|private\s+|protected\s+|abstract\s+|final\s+)?class\s+(\w+)")
# VARIABLE_REGEX = re.compile(r"(?:private|protected|public)?\s+(?:static\s+|final\s+)?(?!return\b)(\w+)\s+(\w+)\s*;")
VARIABLE_REGEX = re.compile(r"(?:private|protected|public)?\s+(?:static\s+|final\s+)?(?!return\b)(\w+(?:<[\w\s,]+>)?)\s+(\w+)\s*;")
JAVA_TYPES = {"boolean", "byte", "short", "char", "int", "long", "float","double", "Integer", "Boolean", "String", "Long", "BigInteger"}   # Java Primitive types 'Set'

KEY_WORDS_SEARCH = ["ultimateEci", "parentEci", "hierarchy", "hier" ] #keywords to find


def clean_up(content:str)->str:
    content_cleanup = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)    #Remove block comments
    after_clean_up = re.sub(r'//.*', '', content_cleanup) #Remove in-line comments
    clean_data = re.sub(r"import\s+.*?;\n|public\s+\w+\s+\w+$$.*?$$\s*{.*?}", "", after_clean_up, flags=re.DOTALL) #Removes imports statements
    return clean_data

def read_file(filepath: str) -> Optional[str]:

    try:
        with open(filepath, 'r', buffering=8192) as file: 
            return file.read()
    except FileNotFoundError: 
        print(f"Error: File not found at {filepath}")
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
    return None


@lru_cache(maxsize=None) #lru -> Least Recently Used strategy. 
def find_java_files_cached(class_name: str) -> str:

    """
    Finds the Java file path for the given class name across all modules
    Caches the results for performance
    """
    for root, _, files in os.walk(search_directory):
        for file in files:
            if file.endswith(".java") and "Test" not in file and file[:-5] == class_name:
                return os.path.join(root, file)



def search_words(java_files: list, directory: str)-> None:

    searchedFiles = set() #Initialzing an empty set to keep track of classes already searched to prevent infinite loops

    for filepath in java_files:
        parent_file_name = None
        class_variables = {}

        #Read content
        content = read_file(filepath)
        if not content:
            continue    

        #Clean content
        cleaned_content = clean_up(content)

        #Extract class name: 
        classMatch = re.search(CLASS_REGEX, cleaned_content)

        if classMatch: #Checks if class definition was found in the current file. 
            # print(f"Full Match: {classMatch.group(0)}")
            parentClassName = classMatch.group(1)  # Extracts the captured class name from the regex match.
            print(f"Extracted Class Name: {parentClassName}")
            
            if parentClassName in searchedFiles:
                continue
            searchedFiles.add(parentClassName)
        else:
            continue    

        #Extract class-level variables with their types
        for match in VARIABLE_REGEX.finditer(cleaned_content):
            var_type = match.group(1) #Extracts the variable type from the regex
            var_name = match.group(2) #Extracts the variable name from the regex


            if ';' in cleaned_content[match.start() :match.end()]:
                # print(f"Extracted Variable Type: {var_type}, Variable Name: {var_name}") 
                class_variables[var_name] = var_type[var_type.find('<') + 1:var_type.find('>')] if '<' in var_type else var_type  #Storing class variables and their types

        foundInParent = False #Intializaing flag to track if the keyword found as a variable in parent class     
        for keyword in KEY_WORDS_SEARCH:
            for var_name in class_variables:
                if keyword.lower() in var_name.lower():
                    print(f"Keyword '{keyword}' found as a substring in variable '{var_name}' of class: {parentClassName}") # Prints a message indicating the found keyword and the class name.
                    foundInParent = True #Sets the flag True as keyword found in the parent class
                    break #Exits the loop since, the match was found in parent level
            if foundInParent:
                break    # Move to the next keyword if found in a variable name

        if not foundInParent and parentClassName:
            for var_name, var_type in class_variables.items():
                if var_type[0].isupper() and var_type not in JAVA_TYPES:
                    java_file_path = find_java_files_cached(var_type)
                    if java_file_path and java_file_path not in searchedFiles:
                        # print(f"Child class found: {java_file_path}")
                        search_in_child(java_file_path, KEY_WORDS_SEARCH, parentClassName, searchedFiles, [parentClassName])                 


                  
def search_in_child(child_filepath: str, keywords: list, parent_class_name: str, searched_classess: set, path_trace: list): 

    #Read file content
    child_content = read_file(child_filepath)
    if not child_content:
        return
    
    #Clean file content
    child_cleaned_content = clean_up(child_content)
    
    match = re.search(CLASS_REGEX, child_cleaned_content)
    if not match:
        return
    
    child_class_name = match.group(1) #Extract name of the child class

    if child_class_name in searched_classess:  # Checks if the child class has already been searched.
        return # If the child class has been searched, exit to prevent cycles.
    
    searched_classess.add(child_class_name) # Adds the child class name to the set of searched classes.

    path_trace.append(child_class_name)

    child_varibles = {}  # Initializes an empty dictionary to store variable names and types of the child class.

    for match in VARIABLE_REGEX.finditer(child_cleaned_content):
        var_type = match.group(1) #Extract variable type
        var_name = match.group(2) #Extract variable name
        child_varibles[var_name] = var_type[var_type.find('<') + 1:var_type.find('>')] if '<' in var_type else var_type #Stores varibles type with its name in the 'child_variables' dictionary

    
    #Keyword search in child variables
    for keyword in keywords:
        for var_name in child_varibles:
            if keyword.lower() in var_name.lower():
                trace_str = " -> ".join(path_trace)
                print(f"Keyword '{keyword}' found in variable '{var_name}' along path: {trace_str}")
                return # Found in child, no need to search further in this branch

    #Recursive search for deeper classes
    for var_name, var_type in child_varibles.items():
        if var_type[0].isupper() and var_type not in JAVA_TYPES and var_type not in searched_classess:
            deeper_path = find_java_files_cached(var_type)
            if deeper_path:
                search_in_child(deeper_path, keywords, child_class_name, searched_classess, path_trace[:])        



def is_valid_java_file(file_path: str):

    """
    Filters class that endsWith ".java" and removes all classes that have name "Test"
    """
    filename = os.path.basename(file_path)
    # return filename.endswith(".java") and "Test" not in filename and os.path.isfile(file_path)
    return filename.endswith(".java") and "Test" not in filename and ( "Response" in filename  or "Request" in filename) and os.path.isfile(file_path)



def filter_java_files_recursive(search_directory: str, max_workers=10) -> list: #max_workers is default set to 30

    """
    Recursively finds all Java Files that have "Request or "Response" of their file name in a directory and subdirectories
    excluding those that contain "Test" in the filename

    Args: 
        directory(str): The directory to search. 

    Returns: 
        list: List of Java files.     

    """

    all_files_paths = []

    for root, _, files in os.walk(search_directory):
        for file in files:
            full_path = os.path.join(root, file)
            all_files_paths.append(full_path)


    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        validity = list(executor.map(is_valid_java_file, all_files_paths))

    java_files = [path for path, is_valid in zip(all_files_paths, validity) if is_valid]

    return java_files       

    

if __name__ == "__main__":

    print(f"\nProgram Start!")

    search_directory = input(f"\nProvide project directory: ") #user to provide directory path

    java_files = filter_java_files_recursive(search_directory)

    if not java_files:
        print(f"No Java Files found in the directory: {search_directory}")
    else:
        print(f"\nFiles found in the directory. Proceeding for next step")   
        search_words(java_files, search_directory) 

    print(f"\n Program Executed")    