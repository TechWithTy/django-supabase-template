import os
import shutil
import sys
import re

def merge_pipfiles(source_pipfile, target_pipfile, target_directory):
    """Merge the dependencies from source Pipfile into target Pipfile
    
    This function handles merging two Pipfiles by intelligently combining their dependencies.
    It avoids duplicating packages that are already present in the target Pipfile.
    
    Args:
        source_pipfile: Path to the source Pipfile (template)
        target_pipfile: Path to the target Pipfile (existing project)
        target_directory: Directory where the merged Pipfile will be saved
        
    Returns:
        bool: True if merge was successful, False otherwise
    """
    if not os.path.exists(source_pipfile) or not os.path.exists(target_pipfile):
        print("Cannot merge Pipfiles: source or target does not exist")
        return False
    
    try:
        # Read both Pipfiles
        with open(source_pipfile, 'r') as source_file:
            source_content = source_file.read()
        
        with open(target_pipfile, 'r') as target_file:
            target_content = target_file.read()
        
        # Extract packages sections from both files
        source_packages = extract_pipfile_section(source_content, 'packages')
        source_dev_packages = extract_pipfile_section(source_content, 'dev-packages')
        
        if not source_packages:
            print("Could not find [packages] section in source Pipfile")
            return False
        
        # Extract individual packages from source
        source_package_dict = parse_pipfile_packages(source_packages)
        source_dev_package_dict = parse_pipfile_packages(source_dev_packages) if source_dev_packages else {}
        
        # Extract sections from target
        target_packages_section = extract_pipfile_section(target_content, 'packages')
        target_dev_packages_section = extract_pipfile_section(target_content, 'dev-packages')
        
        if not target_packages_section:
            print("Could not find [packages] section in target Pipfile")
            return False
            
        # Extract individual packages from target
        target_package_dict = parse_pipfile_packages(target_packages_section)
        target_dev_package_dict = parse_pipfile_packages(target_dev_packages_section) if target_dev_packages_section else {}
        
        # Merge packages (source packages take precedence in case of version conflicts)
        for package, version in source_package_dict.items():
            if package not in target_package_dict:
                target_package_dict[package] = version
            else:
                print(f"Package {package} already exists in target Pipfile with version {target_package_dict[package]}")
                print(f"Keeping version from template: {version}")
                target_package_dict[package] = version
        
        # Merge dev packages
        for package, version in source_dev_package_dict.items():
            if package not in target_dev_package_dict:
                target_dev_package_dict[package] = version
            else:
                print(f"Dev package {package} already exists in target Pipfile with version {target_dev_package_dict[package]}")
                print(f"Keeping version from template: {version}")
                target_dev_package_dict[package] = version
        
        # Rebuild the packages section
        new_packages_section = "[packages]\n"
        for package, version in sorted(target_package_dict.items()):
            new_packages_section += f"{package} = {version}\n"
        
        # Rebuild the dev-packages section
        new_dev_packages_section = "\n[dev-packages]\n"
        for package, version in sorted(target_dev_package_dict.items()):
            new_dev_packages_section += f"{package} = {version}\n"
        
        # Get the parts of the target file outside the packages sections
        target_parts = re.split(r'\[packages\]|\[dev-packages\]', target_content)
        
        # Rebuild the file
        if len(target_parts) >= 2:
            # Has both sections
            merged_content = target_parts[0] + new_packages_section + new_dev_packages_section
        else:
            # Only has packages section
            merged_content = target_parts[0] + new_packages_section
        
        # Write merged content back to target Pipfile
        merged_pipfile_path = os.path.join(target_directory, 'Pipfile')
        with open(merged_pipfile_path, 'w') as merged_file:
            merged_file.write(merged_content)
        
        # Verify the merged Pipfile
        if verify_pipfile(merged_pipfile_path):
            print("Successfully merged Pipfiles and verified the result")
            return True
        else:
            print("Warning: Merged Pipfile may have syntax errors. Please check it manually.")
            return False
    
    except Exception as e:
        print(f"Error merging Pipfiles: {e}")
        return False

def extract_pipfile_section(content, section_name):
    """Extract a section from a Pipfile
    
    Args:
        content: The content of the Pipfile
        section_name: The name of the section to extract (e.g., 'packages', 'dev-packages')
        
    Returns:
        str: The extracted section or None if not found
    """
    section_start = content.find(f'[{section_name}]')
    if section_start == -1:
        return None
        
    # Find the next section or end of file
    next_section = content.find('[', section_start + len(f'[{section_name}]'))
    if next_section == -1:
        section = content[section_start:].strip()
    else:
        section = content[section_start:next_section].strip()
        
    return section

def parse_pipfile_packages(section):
    """Parse packages from a Pipfile section
    
    Args:
        section: The content of a Pipfile section
        
    Returns:
        dict: A dictionary of package names and versions
    """
    if not section:
        return {}
        
    packages = {}
    # Skip the first line which is the section header
    lines = section.split('\n')[1:]
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        # Handle different package specification formats
        if '=' in line:
            parts = line.split('=', 1)
            package = parts[0].strip()
            version = parts[1].strip()
            packages[package] = version
    
    return packages

def verify_pipfile(pipfile_path):
    """Verify that a Pipfile is syntactically correct
    
    This is a simple verification that checks for basic structure.
    For a more thorough check, you would use pipenv to validate the file.
    
    Args:
        pipfile_path: Path to the Pipfile to verify
        
    Returns:
        bool: True if the Pipfile appears valid, False otherwise
    """
    try:
        with open(pipfile_path, 'r') as f:
            content = f.read()
            
        # Check for required sections
        if '[packages]' not in content:
            print("Error: Pipfile is missing [packages] section")
            return False
            
        # Check for balanced quotes
        if content.count('"') % 2 != 0:
            print("Error: Pipfile has unbalanced double quotes")
            return False
            
        if content.count("'") % 2 != 0:
            print("Error: Pipfile has unbalanced single quotes")
            return False
            
        # Check for balanced brackets
        if content.count('[') != content.count(']'):
            print("Error: Pipfile has unbalanced brackets")
            return False
            
        return True
    except Exception as e:
        print(f"Error verifying Pipfile: {e}")
        return False

def copy_files(target_directory):
    # Get the current directory
    current_dir = os.getcwd()
    script_path = os.path.abspath(__file__)
    
    # Check if target has a Pipfile
    target_pipfile = os.path.join(target_directory, 'Pipfile')
    source_pipfile = os.path.join(current_dir, 'Pipfile')
    has_pipfile = os.path.exists(source_pipfile) and os.path.exists(target_pipfile)
    
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
                if item == 'Pipfile' and has_pipfile:
                    # If both source and target have Pipfiles, merge them instead of overwriting
                    merge_result = merge_pipfiles(source_pipfile, target_pipfile, target_directory)
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
