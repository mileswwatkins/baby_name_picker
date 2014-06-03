from collections import namedtuple
import cPickle as pickle
from csv import reader
from operator import itemgetter
import os
import re

from flask import Flask, redirect, render_template
from flask_wtf import Form
from wtforms import IntegerField, RadioField, SelectField, TextField
from wtforms.validators import Required, ValidationError


# Create the Web interface
app = Flask(__name__)
app.config["DEBUG"] = True
app.config["SECRET_KEY"] = "not a website, so not a problem"

# Set local storage paths
default_data_directory = \
        os.path.join(os.path.dirname(__file__), "name_frequency_data")
DEFAULT_DATA_FILE = "yob2013.txt"


def import_name_data(
        source_data_directory=default_data_directory,
        source_data_file=DEFAULT_DATA_FILE
        ):
    """ Import the designated Social Security name frequency dataset """

    input_data_file = os.path.join(source_data_directory, source_data_file)

    names = []
    Name = namedtuple("Name", "name gender frequency")

    with open(input_data_file, 'rb') as import_this:
        file_reader = reader(import_this)
        for observation in file_reader:
            name = Name(observation[0], observation[1], int(observation[2]))
            names.append(name)

    return names


def filter_names(
        names,
        gender="",
        min_length=1, max_length=100,
        min_frequency=1, max_frequency=10000000,
        most_common_rank=1, least_common_rank=10000000,
        does_not_contain=[]
        ):
    """
    Apply filters to a list of names, leaving only those with the
    desired characteristics
    """

    if gender:
        gender_filtered_names = []
        for name in names:
            if name.gender == gender:
                gender_filtered_names.append(name)
    else:
        gender_filtered_names = names

    sorted_names = sorted(
            gender_filtered_names,
            key=itemgetter(2),
            reverse=True
            )
    rank_filtered_names = sorted_names[most_common_rank-1:least_common_rank-1]

    fully_filtered_names = []
    for name in rank_filtered_names:
        passes_all_patterns = True
        for pattern in does_not_contain:
            if passes_all_patterns:
                passes_all_patterns = not re.search(pattern, name.name.lower())

        if min_length <= len(name.name) <= max_length and \
                min_frequency <= name.frequency <= max_frequency and \
                passes_all_patterns:
            fully_filtered_names.append(name.name)

    return fully_filtered_names


def _save_names(names, pickle_file_name="chosen_names.txt"):
    pickle.dump(names, open(pickle_file_name, 'wb'))


def _retrieve_names(pickle_file_name="chosen_names.txt"):
    names = pickle.load(open(pickle_file_name, 'rb'))
    return names


class YearForm(Form):
    year = SelectField("Available Years", coerce=int)


class FilterForm(Form):
    gender = SelectField("Gender", coerce=int)
    min_length = IntegerField("Minimum Length")
    max_length = IntegerField("Maximum Length")
    min_frequency = IntegerField("Minimum Frequency")
    max_frequency = IntegerField("Maximum Frequency")
    most_common_rank = IntegerField("Most Common Rank")
    least_common_rank = IntegerField("Least Common Rank")
    does_not_contain = TextField("Letter Patterns Not Allowed")


@app.route("/import")
def import_view():
    form = YearForm()

    all_files = []
    years_available = []
    for _, _, files in os.walk(default_data_directory):
        all_files.extend(files)
    for each in all_files:
        year_search = re.match("^yob(\d{4}).txt", each)
        if year_search:
            years_available.extend(year_search.groups()[0])
    form.year.choices = years_available

    if form.validate_on_submit():
        data_file = "yob{}.txt".format(form.year.data)
        all_names = import_name_data(source_data_file=data_file)
        _save_names(all_names, pickle_file_name="all_names.txt")
        return redirect("/filter")

    return render_template("import.html", form=form)


if __name__ == '__main__':
    all_names = import_name_data()
    names = filter_names(
            all_names,
            min_length=3, max_length=8,
            min_frequency=100,
            most_common_rank=100,
            does_not_contain=[]
            )
    _save_names(names)
    app.run()
