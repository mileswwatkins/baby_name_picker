import cPickle as pickle
from csv import reader
from operator import itemgetter
import os
import random
import re

from flask import Flask, redirect, render_template
from flask_wtf import Form
from wtforms import BooleanField, IntegerField, RadioField, SelectField, \
        TextField


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
    with open(input_data_file, 'rb') as import_this:
        file_reader = reader(import_this)
        for observation in file_reader:
            name = {}
            name["name"] = observation[0]
            name["gender"] = observation[1]
            name["frequency"] = int(observation[2])
            names.append(name)

    return names


def filter_names(
        names,
        gender="",
        min_length=1, max_length=100,
        min_frequency=1, max_frequency=10000000,
        most_common_rank=1, least_common_rank=10000000,
        does_not_contain=""
        ):
    """
    Apply filters to a list of names, leaving only those with the
    desired characteristics
    """

    if gender:
        gender_filtered_names = []
        for name in names:
            if name["gender"] in gender:
                gender_filtered_names.append(name)
    else:
        gender_filtered_names = names

    sorted_names = sorted(
            gender_filtered_names,
            key=itemgetter("frequency"),
            reverse=True
            )
    rank_filtered_names = sorted_names[most_common_rank-1:least_common_rank-1]

    fully_filtered_names = []
    for name in rank_filtered_names:
        if does_not_contain:
            passes_all_patterns = True
            for pattern in does_not_contain.split(" "):
                if passes_all_patterns:
                    passes_all_patterns = \
                            not re.search(pattern, name["name"].lower())

        if min_length <= len(name["name"]) <= max_length and \
                min_frequency <= name["frequency"] <= max_frequency and \
                passes_all_patterns:
            fully_filtered_names.append(name["name"])

    return fully_filtered_names


def _save_names(names, pickle_file_name):
    pickle.dump(names, open(pickle_file_name, 'wb'))


def _retrieve_names(pickle_file_name):
    names = pickle.load(open(pickle_file_name, 'rb'))
    return names


class YearForm(Form):
    year = SelectField("Available Years", coerce=int)


class FilterForm(Form):
    gender = RadioField("Gender", coerce=int, default=2)
    min_length = IntegerField("Minimum Length", default=1)
    max_length = IntegerField("Maximum Length", default=50)
    min_frequency = IntegerField("Minimum Frequency", default=1)
    max_frequency = IntegerField("Maximum Frequency", default=10000000)
    most_common_rank = IntegerField("Most Common Rank", default=1)
    least_common_rank = IntegerField("Least Common Rank", default=1000000)
    does_not_contain = \
            TextField("Letter Patterns Not Allowed (Delimited by Space)")


@app.route("/import", methods=["GET", "POST"])
def import_view():
    form = YearForm()

    all_files = []
    years_available = []
    for _, _, files in os.walk(default_data_directory):
        all_files.extend(files)
    for each in all_files:
        year_search = re.match("^yob(\d{4}).txt", each)
        if year_search:
            years_available.append(
                    (int(year_search.groups()[0]), year_search.groups()[0])
                    )
    form.year.choices = years_available

    if form.validate_on_submit():
        data_file = "yob{}.txt".format(form.year.data)
        all_names = import_name_data(source_data_file=data_file)
        _save_names(all_names, pickle_file_name="all_names.txt")
        return redirect("/filter")

    return render_template("import.html", form=form)


@app.route("/filter", methods=["GET", "POST"])
def filter_view():
    form = FilterForm()

    GENDER_CHOICES = [(0, "Male"), (1, "Female"), (2, "Male or Female")]
    form.gender.choices = GENDER_CHOICES

    if form.validate_on_submit():
        gender_selection = GENDER_CHOICES[form.gender.data][1]
        all_names = _retrieve_names(pickle_file_name="all_names.txt")
        filtered_names = filter_names(
                all_names,
                gender=gender_selection,
                min_length=form.min_length.data,
                max_length=form.max_length.data,
                min_frequency=form.min_frequency.data,
                max_frequency=form.max_frequency.data,
                most_common_rank=form.most_common_rank.data,
                least_common_rank=form.least_common_rank.data,
                does_not_contain=form.does_not_contain.data
                )
        filtered_names = [all_names[0]["name"], all_names[1]["name"], all_names[2]["name"]]
        _save_names(filtered_names, pickle_file_name="filtered_names.txt")
        _save_names(filtered_names, pickle_file_name="chosen_names.txt")
        return redirect("/choose")

    return render_template("filter.html", form=form)


@app.route("/choose", methods=["GET", "POST"])
def choose_view():
    names = _retrieve_names(pickle_file_name="chosen_names.txt")
    NUMBER_OF_CHOICES = 3
    name_choices = random.sample(names, NUMBER_OF_CHOICES)
    return render_template("choose.html", choices=name_choices)


if __name__ == '__main__':
    app.run()
