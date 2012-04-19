import os
import re

def _find_resource_files(resource_dir, filename_pattern=None):
    if filename_pattern is None:
        filename_pattern = "*"
        
    all_module_filenames = os.listdir(resource_dir)
    resource_filenames = list()
    
    for module_filename in all_module_filenames:
        local_filename = os.path.split(module_filename)[1]
        if re.match(filename_pattern, local_filename):
            resource_filenames.append(local_filename)
        
    return resource_filenames

def _create_resources_dict(resource_dir, resource_filenames):
    # Iterate over all of the resource filenames, adding each to the global
    # namespace, using the file name as the key.
    resources = dict()
    for resource_file_path in resource_filenames:
        full_file_path = os.path.join(resource_dir, resource_file_path)
        resources[resource_file_path] = full_file_path
        
    return resources
