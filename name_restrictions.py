import cPickle as pickle
from csv import reader
from operator import itemgetter
import os
import random
import re
import webbrowser

from flask import Flask, redirect, request, render_template, session
from flask_wtf import Form
from wtforms import BooleanField, IntegerField, RadioField, SelectField, \
        TextField


# Create the Web interface
app = Flask(__name__)
app.config["DEBUG"] = True
app.config["SECRET_KEY"] = "not a website, so not a problem"

# Set local storage paths
local_directory = os.path.dirname(__file__)
default_data_directory = os.path.join(local_directory, "name_frequency_data")
DEFAULT_DATA_FILE = "yob2013.txt"


def import_name_data(
        source_data_directory=default_data_directory,
        source_data_file=DEFAULT_DATA_FILE
        ):
    '''Import the designated Social Security name frequency dataset'''

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
        gendered_names_only=False,
        min_length=1, max_length=100,
        min_frequency=1, max_frequency=10000000,
        most_common_rank=1, least_common_rank=10000000,
        does_not_contain=""
        ):
    '''
    Apply filters to a list of names, leaving only those with the
    desired characteristics
    '''

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

    male_names = [name["name"] for name in names if name["gender"] == "M"]
    female_names = [name["name"] for name in names if name["gender"] == "F"]
    gender_ambiguous_names = [name["name"] for name in names if 
            name["name"] in male_names and name["name"] in female_names]
    if gendered_names_only:
        for name in rank_filtered_names:
            if name["name"] in gender_ambiguous_names:
                rank_filtered_names.remove(name)

    fully_filtered_names = []
    for name in rank_filtered_names:
        passes_all_patterns = True
        if does_not_contain:
            for pattern in does_not_contain.split(" "):
                if passes_all_patterns:
                    passes_all_patterns = \
                            not re.search(
                            pattern.lower(),
                            name["name"].lower())

        if min_length <= len(name["name"]) <= max_length and \
                min_frequency <= name["frequency"] <= max_frequency and \
                passes_all_patterns:
            fully_filtered_names.append(name["name"])

    return fully_filtered_names


def _save_names(names, pickle_file_name):
    '''Utility function to save a list of names to disk'''
    pickle.dump(names, open(pickle_file_name, 'wb'))


def _retrieve_names(pickle_file_name):
    '''Utility function to retrieve a list of names from disk'''
    names = pickle.load(open(pickle_file_name, 'rb'))
    return names


class YearForm(Form):
    year = SelectField("Available Years", coerce=int)


class FilterForm(Form):
    gender = RadioField("Gender", coerce=int, default=2)
    gendered_names_only = BooleanField(
            "Only Allow Names with Unambigous Gender",
            default=False
            )
    min_length = IntegerField("Minimum Length", default=1)
    max_length = IntegerField("Maximum Length", default=50)
    min_frequency = IntegerField("Minimum Frequency", default=1)
    max_frequency = IntegerField("Maximum Frequency", default=10000000)
    most_common_rank = IntegerField("Most Common Rank", default=1)
    least_common_rank = IntegerField("Least Common Rank", default=2500)
    does_not_contain = \
            TextField("Letter Patterns Not Allowed (Delimited by Space)")


@app.route("/", methods=["GET"])
def default_view():
    '''Reroutes user to the appropriate step in the process'''

    all_files = []
    for _, _, files in os.walk(local_directory):
        all_files.extend(files)
    print(local_directory)
    print(all_files)
    if "chosen_names.txt" in all_files:
        return redirect("/choose")
    elif "filtered_names.txt" in all_files:
        return redirect("/choose")
    elif "all_names.txt" in all_files:
        return redirect("/filter")
    else:
        return redirect("/import")


@app.route("/import", methods=["GET", "POST"])
def import_view():
    '''Select and import one year of the Social Security name data'''

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
    '''For the selected year of data, filter out unwanted types of names'''

    form = FilterForm()

    GENDER_CHOICES = [(0, "Male"), (1, "Female"), (2, "Male or Female")]
    form.gender.choices = GENDER_CHOICES

    if form.validate_on_submit():
        gender_selection = GENDER_CHOICES[form.gender.data][1]
        all_names = _retrieve_names(pickle_file_name="all_names.txt")
        filtered_names = filter_names(
                all_names,
                gender=gender_selection,
                gendered_names_only=form.gendered_names_only.data,
                min_length=form.min_length.data,
                max_length=form.max_length.data,
                min_frequency=form.min_frequency.data,
                max_frequency=form.max_frequency.data,
                most_common_rank=form.most_common_rank.data,
                least_common_rank=form.least_common_rank.data,
                does_not_contain=form.does_not_contain.data
                )
        _save_names(filtered_names, pickle_file_name="filtered_names.txt")
        _save_names(filtered_names, pickle_file_name="chosen_names.txt")
        return redirect("/choose")

    return render_template("filter.html", form=form)


@app.route("/choose", methods=["GET", "POST"])
def choose_view():
    '''
    Provide the user a choice between a set of names from the filtered
    list, and remove those that are not chosen
    '''

    name_to_keep = request.form.get("button")
    name_choices = session.get("name_choices", None)
    if name_to_keep and name_choices and name_to_keep in name_choices:
        names = _retrieve_names(pickle_file_name="chosen_names.txt")
        for name in name_choices:
            if name != name_to_keep:
                names.remove(name)
        _save_names(names, pickle_file_name="chosen_names.txt")

    names = _retrieve_names(pickle_file_name="chosen_names.txt")
    NUMBER_OF_CHOICES = 3
    try:
        session["name_choices"] = random.sample(names, NUMBER_OF_CHOICES)
        return render_template("choose.html", choices=session["name_choices"])
    except ValueError:
        return redirect("/names_remaining")


@app.route("/names_remaining", methods=["GET"])
def names_remaining_view():
    '''Provide a quick view of which names remain'''
    names = _retrieve_names(pickle_file_name="chosen_names.txt")
    return render_template("names_remaining.html", names=names)


if __name__ == '__main__':
    # app.run()
    with open(variant_data_file, 'rb') as import_this:
        file_reader = reader(import_this)
        for observation in file_reader:
            name_variants = {}
            name_variants["name"] = observation[0]
            name_variants["variants"] = observation[2].split(" ")
            all_name_variants.append(name_variants)
