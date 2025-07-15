import os

def getAllFilesInDirectory(directory, full_path = True):
    files_in_directory = []
    for entry in os.listdir(directory):
        full_path_file = os.path.join(directory, entry)
        if os.path.isfile(full_path_file) and not "~" in full_path_file:
            if full_path:
                files_in_directory.append(full_path_file)
            else:
                files_in_directory.append(entry)
    return files_in_directory

def convertDataframeToDictionary(df):
    df_indexed = df.set_index("Name")["Value"]
    config_dict = df_indexed.to_dict()
    return config_dict
