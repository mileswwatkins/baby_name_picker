from collections import namedtuple
from csv import reader
from operator import itemgetter
import os
import re


DEFAULT_DATA_PATH = os.path.join(os.path.dirname(__file__), "name_frequency_data")

def import_name_data(source_data_directory=DEFAULT_DATA_PATH):
    # Identify the most recent data file
    data_files = []
    for _, _, files in os.walk(source_data_directory):
        data_files.extend(files)

    # Cheating, will replace
    most_recent_data_file = os.path.join(source_data_directory, "yob2013.txt")

    # Import all name data from that file
    names = []
    Name = namedtuple("Name", "name gender frequency")
    with open(most_recent_data_file, 'rb') as import_this:
        file_reader = reader(import_this)
        for observation in file_reader:
            name = Name(observation[0], observation[1], observation[2])
            names.append(name)

    return names


def filter_names(
        names,
        gender="MF",
        min_length=1, max_length=100,
        min_rank=1, max_rank=10000000
        ):
    gender_filtered_names = []
    for name in names:
        if name.gender in gender:
            gender_filtered_names.append(name)

    sorted_names = sorted(
            gender_filtered_names,
            key=itemgetter(2),
            reverse=True
            )
    rank_filtered_names = sorted_names[min_rank-1:max_rank-1]

    fully_filtered_names = []
    for name in rank_filtered_names:
        if min_length <= len(name.name) <= max_length:
            fully_filtered_names.append(name.name)

    return fully_filtered_names


if __name__ == '__main__':
    all_names = import_name_data()
    print(len(all_names))
    names = filter_names(
            all_names,
            gender="M",
            min_length=3, max_length=8,
            min_rank=100, max_rank=10000
            )
    print(len(names))
