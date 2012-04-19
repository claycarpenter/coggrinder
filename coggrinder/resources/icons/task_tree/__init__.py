from coggrinder import resources
import os

def _load_resources():
    resource_dir = os.path.dirname(__file__)
    resource_filenames = resources._find_resource_files(resource_dir, ".*\.png")
    
    return resources._create_resources_dict(resource_dir, resource_filenames)
 
FILES = _load_resources() 