import requests
from bs4 import BeautifulSoup
import json
import time
import pandas as pd
from datetime import datetime
import re

time.sleep(60 * 60)
# url needed to get the most recent 100 contributors of hadoop
initial_url = "https://api.github.com/repos/apache/hadoop/contributors?per_page=100&page="
# access token to get the data with multiple requests
personal_access_token = ""
# creates the headers to use in the get request
header = {"Authorization": "token " + personal_access_token}


# go to the desired url for the api and return the data as a json object
def collect_data(url):
    # uses the get request to pull data from the desired url which was passed into the function
    api = requests.get(url, headers=header)
    # cleans up the returned data using the beautifulsoup package
    doc = BeautifulSoup(api.content, 'html.parser')
    # remove these random emails at the end of the file
    doc = str(doc)
    if "https://api.github.com/repos/apache/hadoop/commits?per_page=100" in url:
        doc = doc.replace(str(re.findall("<\/.*@.*\..*>", doc)[0]), "")
    # creates a json object to be returned
    json_dict = json.loads(doc)
    return json_dict


# get the information on the repo
def get_repo(login_id):
    # sets the first page
    pages = 1
    # collects the data of the 100 repos the user has based on the login_id
    repos = collect_data("https://api.github.com/users/" + login_id + "/repos?per_page=100")
    num_cont = []
    repo_names = []
    # while the number of repos a user has is 100 run the loop
    # in order to determine the total number of repos a user has you need to paginate
    # the max number of repos that can be returned in one call is 100 so if the user has more than 100
    # find the rest of the repos
    while len(repos) == 100:
        # loop through each of the users repos on the current page
        for repo in repos:
            # get the number of contributions the user has for each repo
            num_cont.append(repo_contributions(login_id, repo))
            # save the name of each repo
            repo_names.append(repo['name'])
        # increase the number of pages that have been run through
        pages = pages + 1
        # collect the next page of repos
        repos = collect_data("https://api.github.com/users/" + login_id + "/repos?per_page=100&page=" + str(pages))
    # loop through the users repos for when the user is not at the max number of repos per page (100)
    for repo in repos:
        # get the number of contributions the user has for each repo
        num_cont.append(repo_contributions(login_id, repo))
        # save the name of each repo
        repo_names.append(repo['name'])
    # get the total number of repos the user has
    num_repo = len(repos) + 100 * (pages - 1)
    # return the login_id of the user, the number of repos the user has, the names of the repos,
    # and the number of contributions the user made
    return login_id, num_repo, repo_names, num_cont


# get the number of  contributions made to the repo
def repo_contributions(id, repo):
    # check for issues in the data where the size of the repo is 0 or there is no language set for the repo
    if repo['size'] == 0 or repo['language'] == None:
        # check for if there is an error message in the returned data
        if "message" in collect_data("https://api.github.com/repos/" + id + "/" + repo['name'] + "/contents"):
            return None
    # if there are no issues in the data collect the number of contributions and if they have contributed to the repo
    user_data = collect_data(repo["contributors_url"] + "?per_page=100")
    # loop through each user in the data and if they have the user id of the user we are looking at
    # return the number of contributions they have made for the repo
    for user in user_data:
        if user['login'] == id:
            # return here as this will break the loop and save time from not running through all the users in every repo
            # as this would likely add a lot to the runtime
            return user['contributions']
    return 0


# get the time data for the difference between the most recent and 100th commit
def get_time():
    # collects the data to use to determine the difference in the most recent and 100th commit
    time_data = collect_data("https://api.github.com/repos/apache/hadoop/commits?per_page=100")
    # gets the most recent piece of data
    recent_data = time_data[0]['commit']['author']['date'].replace("Z", "")
    # fixes the data so it can be used in the datetime calculations
    recent_data = recent_data.replace("T", " ")
    # takes only the datetime component of the recent data
    recent = datetime.strptime(recent_data, '%Y-%m-%d %H:%M:%S')
    # gets the data at the end of the list
    old_data = time_data[-1]['commit']['author']['date'].replace("Z", "")
    # fixes the data so it can be used in the datetime calculations
    old_data = old_data.replace("T", " ")
    # takes only the date time component of the oldest data
    old = datetime.strptime(old_data, '%Y-%m-%d %H:%M:%S')
    # returns the absolute difference between the most recent and 100th(oldest) commit
    return abs(recent - old)


# list to store the contributions
cont_data = []
# get the 100 users
data = collect_data(initial_url + str(1))
# sets the initial count of people in the data
people_count = 1
# print the time difference
print(get_time())
# for each variable get the desired data
for person in range(0, len(data)):
    # increase the number of people in the data
    people_count = people_count + 1
    # gets the login_id of the user, the number of repos the user has, the names of the repos,
    # and the number of contributions the user made
    num_repo = get_repo(data[person]['login'])
    # gets the number of repos
    cont_data.append(num_repo)
# put the data into a dataframe for pretty viewing
final_data = pd.DataFrame(cont_data, columns=['User', 'Number of Repos', 'Repo Names', 'Number of Contributions'])
pd.set_option("display.max_rows", None, "display.max_columns", None)
print(final_data)
