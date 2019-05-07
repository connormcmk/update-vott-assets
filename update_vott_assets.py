import subprocess
import fileinput
import hashlib
import click
import json
import glob
import sys
import os
import re

def get_single_file_with_suffix(directory, suffix):
    """
    Return the file in directory with the specified suffix. 
    
    If none is found, error. 
    If more than one found, error. 
    
    Args: 
    directory: the path (relative or full) to the directory with the file in it.
    suffix: the suffix of the file *including* the '.' (e.g. '.png' not 'png'). 
    suffix: can also be a list of suffixes to try (e.g. ['.jpg', '.jpeg'])
    """
    candidate_files = []
    if type(suffix) is list:
        # rename suffix to suffixes to make list comprehension more readable
        suffixes = suffix
        # this monster gets all the filenames that end in the suffix found in suffixes and flattens into a single list
        candidate_files = [filename for suffix in suffixes for filename in \
                    glob.glob(os.path.join(directory, '*{}'.format(suffix)))]
        
    elif type(suffix) is str:
        # if only a single string is passed, the files that end in it
        candidate_files = glob.glob(os.path.join(directory, '*{}'.format(suffix)))

    if len(candidate_files) > 1:
        raise Exception("Should have no more than one '{}' file in {}".format(suffix, directory))
    elif len(candidate_files) == 0: 
        raise Exception("No file found with suffix '{}' in {}".format(suffix, directory))
    else: 
        final_file = candidate_files[0]
        
    return final_file

def map_old_vott_path_and_id_to_new(vott_dict, directory_name):
    """
    Return a mapping of the old ids to the new ids
    
    new ids are the md5 hash of the full path (including %20 as whitespace) to the source asset
    """
        
    # initialize the dictionary to contain the mapping
    old_to_new_ids = {}
    
    # iterate through all the assets
    for asset in vott_dict['assets'].values():
        # get what will be the new path of the source asset
        source_asset_path = 'file:'+os.path.join(directory_name, asset['name'])

        # map the old id to the hexdigest of the full path to the source asset
        old_to_new_ids[asset['id']] = hashlib.md5(source_asset_path.encode('utf-8')).hexdigest()
        
    return old_to_new_ids

@click.argument('new_source_directory', type=click.Path(exists=True, file_okay=False,\
            resolve_path=True, readable=True), required=True)
@click.argument('target_directory', type=click.Path(exists=True, file_okay=False,\
            resolve_path=True, readable=True), required=True)
@click.command()
def main(new_source_directory, target_directory):
    """
    Arguments:
    
    target_directory -- the path to the directory that contains all the -asset.json files and the 
    .vott file
    
    new_source_directory -- the path to the directory that contains the images that were
    originally tagged (not yet tested with videos)
    
    Note that the new_source_directory must contain ALL of the assets that were originally present
    in the labeling process.
    
    \b
    
    
    
    Purpose:
    
    This script solves the problem of transferring assets labeled with VoTT from one machine to
    another. 
    
    The problem arises due to VoTT using the md5 hash of the absolute path of the source asset
    (image or video) as the asset_id. This id is used whenever the asset is looked up, so transferring
    assets and VoTT files from one machine to another breaks VoTT's ability to recognize the labels
    because the filepath on two different machines look different (different usernames are enough to
    cause the problem). 
    
    Running this script solves the problem by creating a new asset id for each asset in the provided
    new_source_directory and updating the contents of the target_directory files to reference those
    asset ids.
    """
    
    # npm uses %20 in place of spaces
    npm_ready_new_source_directory = re.sub(' ', '%20', new_source_directory)
    
    # get the vott file that references all the asset files
    vott_file = get_single_file_with_suffix(target_directory, '.vott')
    
    # get a dictionary representation of the vott file
    with open(vott_file, 'r') as f:
        vott_dict = json.load(f)
    
    # get the value of the 'path' key out of the the vott dictionary (a string referencing the old file)
    path_value = list(vott_dict['assets'].values())[0]['path']
    
    # get the source directory of the old files (to substitute with the new one)
    # e.g. keep the '/home/dir' part of 'file:/home/dir/file.txt'
    old_source_directory = os.path.split(path_value[len('file:'):])[0]
    
    # get a dictionary that maps the old asset ids to the new ones
    old_to_new_ids = map_old_vott_path_and_id_to_new(vott_dict, npm_ready_new_source_directory)
    
    print("Replacing old asset ids in file names with the new asset ids")
    for old_asset_path in glob.glob(os.path.join(target_directory, '*-asset.json')):
        # get the basename of the old_asset
        old_asset_file = os.path.basename(old_asset_path)
        
        # get the asset id out of the asset.json file
        # i.e. the ba4eb9e76e2148bb7dc5b82bdccb7dbc in ba4eb9e76e2148bb7dc5b82bdccb7dbc-asset.json
        old_asset_id = old_asset_file.split('-')[0]
        
        # look up the new id to use for this file
        new_id = old_to_new_ids[old_asset_id]
        
        # rename the file so that it has the new asset id in its name, replacing the old one
        os.rename(old_asset_path, os.path.join(target_directory, new_id+'-asset.json'))
    
    print("Replacing old paths and asset ids in the files themselves, this may take a while.")
    
    # get the full path of all files in the target directory, exclude directories
    files = [f for f in glob.glob(os.path.join(target_directory, '*')) if os.path.isfile(f) == True]
    
    # open an inplace fileinput so that stdout of this script becomes the input to the provided files
    for line in fileinput.input(files=files, inplace=True):
        
        # replace every instance of the old id in every file with the proper new id
        for id_pair in old_to_new_ids.items():
            # the old asset id
            old_id = id_pair[0]
            # the new asset id
            new_id = id_pair[1]
            # replace the old id with the new one in this line
            line = line.replace(old_id, new_id)
        
        # replace the old directory name with the new one in this line
        line = line.replace(old_source_directory, npm_ready_new_source_directory)
        
        # the fileinput stream is open (thanks to inplace=True) so everything that goes to stdout
        # goes into the original file (idgi, just works™)
        sys.stdout.write(line)
        
    
    # some variables used in the final instructions
    source_connection = vott_dict['sourceConnection']['name']
    
    target_connection = vott_dict['targetConnection']['name']
    
    security_token_name = vott_dict['securityToken']
    
    final_instructions = '''
Done! Only a couple remaining steps:

    1. Open VoTT
    2. Click Home then click Open Local Project
    3. Navigate to '{target_directory}'
    4. Open the '{vott_file}' file. If it opens without error, you're done! Otherwise:
        - You get Error loading project file: You need to add the right security token
            1. Click Settings (the gear icon)
            2. Ensure you have a listing for '{security_token}' and the right key 
            (I can't help you there, ask the person that originally labeled these assets)
            3. Try loading the '{vott_file}' file again.
        
        and/or
            
        - You get an unknown error: You need to update your Connections
            1. Click the Plug icon
            2. Update '{}' by pointing its connection to:
               '{}'
            3. Update '{}' by pointing its connection to:
               '{target_directory}'
               
            Make sure to hit the Save button after editing.
            
            4. Try loading the '{vott_file}' file again. It should now work!
    '''.format(source_connection, new_source_directory,  
                target_connection, security_token = security_token_name, 
                target_directory = target_directory, vott_file = os.path.basename(vott_file))
    print(final_instructions)


if __name__ == '__main__':
    main()