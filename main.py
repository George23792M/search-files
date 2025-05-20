import os #Import for operating system functions (eg. file path manipuliation)
from concurrent.futures import ThreadPoolExecutor, as_completed #Import to use multithreading
import re #Import the 're' module to use regular expression


CLASS_REGEX = r"\b(?:public\s+|private\s+|protected\s+|abstract\s+|final\s+)?class\s+(\w+)"
VARIABLE_REGEX = VARIABLE_REGEX = r"(?:private|protected|public)?\s+(?:static\s+|final\s+)?(?!return\b)(\w+)\s+(\w+)\s*;"
JAVA_TYPES = ["boolean", "byte", "short", "char", "int", "long", "float","double", "Integer", "Boolean", "String", "Long"]   # Java Primitive types and String

KEY_WORDS_SEARCH = ["ultimateEci", "parentEci", "hierarchy", "hier" ] #keywords to find


def clean_up(content:str)->str:
    content_cleanup = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)    #Remove block comments
    after_clean_up = re.sub(r'//.*', '', content_cleanup) #Remove in-line comments
    clean_data = re.sub(r"import\s+.*?;\n|public\s+\w+\s+\w+$$.*?$$\s*{.*?}", "", after_clean_up, flags=re.DOTALL) #Removes imports statements
    return clean_data


def search_words(java_files: list)-> None:

    searchedFiles = set() #Initialzing an empty set to keep track of classes already searched to prevent infinite loops

    for filepath in java_files:
        parent_file_name = None
        class_variables = {}

        try:
            with open(filepath, 'r') as file: #Open each java file in read mode
                content = file.read() #Read entire java file into content variable 
        except FileNotFoundError:
            print(f"Error: File not found at {filepath}")
            continue
        except Exception as e:
            print(f"Error reading file {filepath}: {e}")
            continue        


        #Cleanup
        cleaned_content = clean_up(content)

        #Extract class name: 
        classMatch = re.search(CLASS_REGEX, cleaned_content)

        if classMatch: #Checks if class definition was found in the current file. 
            # print(f"Full Match: {classMatch.group(0)}")
            parentClassName = classMatch.group(1)  # Extracts the captured class name from the regex match.
            # print(f"Extracted Class Name: {parentClassName}")
            
            if parentClassName in searchedFiles:
                continue
            searchedFiles.add(parentClassName)
        else:
            continue    

        #Extract class-level variables with their types
        for match in re.finditer(VARIABLE_REGEX, cleaned_content):
            var_type = match.group(1) #Extracts the variable type from the regex
            var_name = match.group(2) #Extracts the variable name from the regex

            if ';' in cleaned_content[match.start() :match.end()]:
                # print(f"Extracted Variable Type: {var_type}, Variable Name: {var_name}") 
                class_variables[var_name] = var_type #Storing class variables and their types

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
                    potential_filepath = os.path.join(os.path.dirname(filepath), f"{var_type}.java")
                    if os.path.exists(potential_filepath):
                        search_in_child(potential_filepath, KEY_WORDS_SEARCH, parentClassName, searchedFiles)

def search_in_child(child_filepath: str, keywords: list, parent_class_name: str, searched_classess: set): 

    try:
        with open(child_filepath, 'r') as file: 
            child_content = file.read()
    except FileNotFoundError: 
        print(f"Error: Child class file not found at {child_filepath}")
        return
    except Exception as e:
        print(f"Error reading child class file {child_filepath}: {e}")
        return
    
    child_class_match = re.search(CLASS_REGEX, child_content)
    if not child_class_match:
        return
    child_class_name = child_class_match.group(1) #Extract name of the child class

    if child_class_name in searched_classess:  # Checks if the child class has already been searched.
        return # If the child class has been searched, exit to prevent cycles.
    searched_classess.add(child_class_name) # Adds the child class name to the set of searched classes.

    child_varibles = {}  # Initializes an empty dictionary to store variable names and types of the child class.

    for match in re.finditer(VARIABLE_REGEX, child_content):
        var_type = match.group(1) #Extract variable type
        var_name = match.group(2) #Extract variable name
        child_varibles[var_name] = var_type #Stores varibles type with its name in the 'child_variables' dictionary
    

    for keyword in keywords:
        for var_name in child_varibles:
            if keyword.lower() in var_name.lower():
                print(f"Keyword '{keyword}' found as a substring in variable '{var_name}' of the child class: {child_class_name}, referred by parent class: {parent_class_name}")
                return # Found in child, no need to search further in this branch



def is_valid_java_file(file_path: str):

    """
    Filters class that endsWith ".java" and removes all classes that have name "Test"
    """
    filename = os.path.basename(file_path)
    return filename.endswith(".java") and "Test" not in filename and ( "Response" in filename  or "Request" in filename) and os.path.isfile(file_path)



def filter_java_files_recursive(search_directory: str, max_workers=25) -> list: #max_workers is default set to 25

    """
    Recursively finds all Java Files in a directory and subdirectories
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
        search_words(java_files) 

    print(f"\n Program Executed")    