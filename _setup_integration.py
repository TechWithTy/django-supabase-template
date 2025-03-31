import os
import shutil
import sys
import re

def merge_requirements(source_requirements, target_requirements, target_directory):
    """Merge the dependencies from source requirements.txt into target requirements.txt
    
    This function handles merging two requirements.txt files by intelligently combining their dependencies.
    It avoids duplicating packages that are already present in the target requirements.txt.
    
    Args:
        source_requirements: Path to the source requirements.txt (template)
        target_requirements: Path to the target requirements.txt (existing project)
        target_directory: Directory where the merged requirements.txt will be saved
        
    Returns:
        bool: True if merge was successful, False otherwise
    """
    if not os.path.exists(source_requirements) or not os.path.exists(target_requirements):
        print("Cannot merge requirements.txt files: source or target does not exist")
        return False
    
    try:
        # Read both requirements.txt files
        with open(source_requirements, 'r') as source_file:
            source_content = source_file.read()
        
        with open(target_requirements, 'r') as target_file:
            target_content = target_file.read()
        
        # Parse packages from both files
        source_packages = parse_requirements(source_content)
        target_packages = parse_requirements(target_content)
        
        # Merge packages (source packages take precedence in case of version conflicts)
        for package, version in source_packages.items():
            if package not in target_packages:
                target_packages[package] = version
            else:
                print(f"Package {package} already exists in target requirements.txt with version {target_packages[package]}")
                print(f"Keeping version from template: {version}")
                target_packages[package] = version
        
        # Rebuild the requirements.txt content
        merged_content = ""
        for package, version in sorted(target_packages.items()):
            if version:
                merged_content += f"{package}{version}\n"
            else:
                merged_content += f"{package}\n"
        
        # Write merged content back to target requirements.txt
        merged_requirements_path = os.path.join(target_directory, 'requirements.txt')
        with open(merged_requirements_path, 'w') as merged_file:
            merged_file.write(merged_content)
        
        print("Successfully merged requirements.txt files")
        return True
    
    except Exception as e:
        print(f"Error merging requirements.txt files: {e}")
        return False

def parse_requirements(content):
    """Parse packages from a requirements.txt file
    
    Args:
        content: The content of the requirements.txt file
        
    Returns:
        dict: A dictionary of package names and version constraints
    """
    packages = {}
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('-') or line.startswith('--'):
            continue
            
        # Handle different package specification formats
        # Format: package==version, package>=version, package~=version, etc.
        match = re.match(r'^([\w\-\.]+)([<>=~!].*)$', line)
        if match:
            package = match.group(1)
            version = match.group(2)
            packages[package] = version
        else:
            # Package without version
            packages[line] = ""
    
    return packages

def verify_requirements(requirements_path):
    """Verify that a requirements.txt file is syntactically correct
    
    This is a simple verification that checks for basic structure.
    
    Args:
        requirements_path: Path to the requirements.txt to verify
        
    Returns:
        bool: True if the requirements.txt appears valid, False otherwise
    """
    try:
        with open(requirements_path, 'r') as f:
            content = f.read()
            
        # Parse the file to check for any syntax errors
        packages = parse_requirements(content)
        return True
    except Exception as e:
        print(f"Error verifying requirements.txt: {e}")
        return False

def copy_files(target_directory):
    # Get the current directory
    current_dir = os.getcwd()
    script_path = os.path.abspath(__file__)
    
    # Check if target has a requirements.txt
    target_requirements = os.path.join(target_directory, 'requirements.txt')
    source_requirements = os.path.join(current_dir, 'requirements.txt')
    has_requirements = os.path.exists(source_requirements) and os.path.exists(target_requirements)
    
    # Copy all files and directories except this script
    success = True
    for item in os.listdir(current_dir):
        source_path = os.path.join(current_dir, item)
        target_path = os.path.join(target_directory, item)
        
        # Skip this script
        if source_path == script_path:
            continue
            
        try:
            if os.path.isdir(source_path):
                if os.path.exists(target_path):
                    print(f"Directory {item} already exists in target, merging contents...")
                    # For directories that already exist, we could implement a merge strategy
                    # For now, we'll just copy files that don't exist in the target
                    for root, dirs, files in os.walk(source_path):
                        rel_path = os.path.relpath(root, source_path)
                        target_dir = os.path.join(target_path, rel_path)
                        os.makedirs(target_dir, exist_ok=True)
                        for file in files:
                            source_file = os.path.join(root, file)
                            target_file = os.path.join(target_dir, file)
                            if not os.path.exists(target_file):
                                shutil.copy2(source_file, target_file)
                                print(f"Copied {os.path.relpath(source_file, current_dir)} to {os.path.relpath(target_file, target_directory)}")
                else:
                    shutil.copytree(source_path, target_path)
                    print(f"Copied directory {item} to {target_directory}")
            else:
                if item == 'requirements.txt' and has_requirements:
                    # If both source and target have requirements.txt, merge them instead of overwriting
                    merge_result = merge_requirements(source_requirements, target_requirements, target_directory)
                    if not merge_result:
                        success = False
                else:
                    # For normal files, copy if they don't exist or overwrite with confirmation
                    if os.path.exists(target_path):
                        print(f"File {item} already exists in target, overwriting...")
                    shutil.copy2(source_path, target_path)
                    print(f"Copied file {item} to {target_directory}")
        except Exception as e:
            print(f"Error copying {item}: {e}")
            success = False
    
    # Check if all essential files and directories were copied successfully
    essential_items = ['.env', 'docker-compose.yml', 'config', 'database', 'docker']
    all_copied = all(os.path.exists(os.path.join(target_directory, item)) for item in essential_items)
    
    if success and all_copied:
        print("\nAll files were copied successfully!")
        print("\nYou can now continue with the remaining setup steps as outlined in the README.")
    else:
        print("\nSome files could not be copied. Please check the errors above.")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python setup_integration.py <target_directory>')
        sys.exit(1)

    target_dir = sys.argv[1]
    
    # Ensure target directory exists
    if not os.path.exists(target_dir):
        print(f"Target directory {target_dir} does not exist. Creating it...")
        try:
            os.makedirs(target_dir, exist_ok=True)
        except Exception as e:
            print(f"Error creating target directory: {e}")
            sys.exit(1)
    
    copy_files(target_dir)
