import random
import time
import requests
import json
from bs4 import BeautifulSoup
import re
import os
import pymongo
import beepy
from nltk.corpus import brown
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import pandas as pd
# If you need to dowlonad the nltk corpora
# import nltk
# nltk.download()
platforms_url = "https://api.rawg.io/api/platforms"
games_url = "https://api.rawg.io/api/games"
api_key = "?key=0c02bb604d3c4b51aa12d2f600558a36"
popular_query = "&platforms=4&dates=2020-01-01,2021-12-31&ordering=-added&page_size=40&page="
metacritic_query = "&platforms=4&ordering=-metacritic&dates=2020-01-01,2021-12-31&page_size=40&page="

# collects the data from the api and returns it as a json dictionary
def api_data(url):
    # pull in the data from the api based on the url provided in the call of this function
    api = requests.get(url)
    # collect the content of the api get
    doc = BeautifulSoup(api.content, 'html.parser')
    # stores the data as a json_dict and handles one specific issue present in the data
    json_dict = json.loads(re.sub(r'"The Seven"', 'The Seven', str(doc)))
    # return the json dictionary
    return json_dict

# get html content from the desired url and return it as a beauticul soup object
def get_html(url = "https://www.metacritic.com/"):
    # The headers needed to use for the html call
    headers = {'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"}
    # get the html data from the url passed into the function - default is 'https://www.metacritic.com/'
    html = requests.get(url, headers = headers)
    # get the content from the html data pulled from the url
    html_content = BeautifulSoup(html.content, 'html.parser')
    return html_content

# get the text data based on the specific css reference
def get_text(html_doc, reference):
    # select only the css refrences desired
    element = html_doc.select(str(reference))
    element_content = []
    # for each of the elements found above get the text data for each element and put it into a list
    for input_item in element:
        element_content.append(input_item.get_text())
    # return the desired content
    return element_content

# save html file with the desired file name to the disk
def save_html(html_file, game_name):
    # create the filename for the html data to be saved
    filename = game_name + '.html'
    # create/open the file
    file = open(filename, 'w', encoding='utf-8')
    # write the file as string to the opened file
    file.write(str(html_file))
    #close the file
    file.close()
    return

# Opens the html file from the disc
def open_html(html_filename):
    # open the file with the desired filename
    html_file = open(html_filename, 'r', encoding='utf-8').read()
    # read the data into the desired format
    html_results = BeautifulSoup(html_file, 'lxml')
    return html_results

# stores many data documents to the collection name in mongoDB
def store_many_mongodb(data, collection):
    # open the mongodb instance - in this case it is on my localhost at the port 27017
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    # select the client for the MongoDb instance
    mydb  = myclient['BAX422final']
    # select the collection based on the collection parameter
    mycol = mydb[collection]
    # insert the many data points based on the data passed into the function
    mycol.insert_many(data)

# gets the data from a collection based on the query and projection from mongoDB
def get_data_mongo(collection, query, projection):
    # open the mongodb instance - in this case it is on my localhost at the port 27017
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    # select the client for the MongoDb instance
    mydb  = myclient['BAX422final']
    # select the collection based on the collection parameter
    mycol = mydb[collection]
    # return the data based on the query and projection parameters
    return mycol.find(query, projection=projection)

# combine the most popular and highest metacritic rated games and return the game data for the games in both lists
def combine_data_api(pages):
    # create multiple lists for collecting the data
    popular_games_list = []
    metacritic_games_list = []
    metacritic_games = []
    popular_games = []
    # get the games which have high metacritic ratings and are most popular on the RAWG api
    for page in range(1, pages + 1):
        # collect the games which have the highest reviews on metacritic
        metacritic_games.extend(api_data(games_url + api_key + metacritic_query + str(page))['results'])
        # collect the games which are most popular on the RAWG api
        popular_games.extend(api_data(games_url + api_key + popular_query + str(page))['results'])
    # collect the game id for each of the games in the metacritic and popular games lists
    for game in range(0,len(metacritic_games)):
        if metacritic_games[game]['slug'] != 'final-fantasy-vii-remake':
            metacritic_games_list.append(metacritic_games[game]['id'])
        popular_games_list.append(popular_games[game]['id'])
    # get a list of only the games which have high metactiric ratings and are popular
    games = list(set(metacritic_games_list).intersection(popular_games_list))
    db = []
    # create a list with all the games which are in both the most popular and have high metacritic reviews
    for id in metacritic_games:
        # check and only append the games which are in both the metacritic and popular games lists
        if id['id'] in games:
            db.append(id)
    # return the list of game id's which are going to be used in this analysis
    return db

# collect the urls for the metacritic pages of the game with specific game id
def collect_metacritic_urls(game_ids):
    # create a dictionary to store the metacrtic urls
    metacritic_urls = {}
    # go through each game id and get the metacritic url from the api
    for id in game_ids:
        # get the data from the RAWG api specific to the desired game based on the api game id- games_url refers to the RAWG api url stored at the top of this file
        api = api_data(games_url + '/' +str(id) + api_key)
        # if there is a metactiric url in the data
        if api['metacritic_url']:
            # remove any possible console reviews as we are focusing on pc reviews
            metacritic_urls[api['slug']] = re.sub(r"playstation-4|playstation-5|xbox-one|xbox-series-x", 'pc', api['metacritic_url'])
        # if there is no metacritic url
        else:
            # create the url based on the standard url design metacritic uses to identify pc games review pages
            metacritic_urls[api['slug']] = 'https://www.metacritic.com/game/pc/' + re.sub(r"-\(.*\)", "", api['name'].replace(' ', '-').lower())
    # return the dictionary of metacritic urls that have been collected
    return metacritic_urls

# convert the dictionary into a bunch of lists so the data can be stored in mongoDB
def dict_lists_to_list_dict(dict):
    nl = []
    nl_index = []
    # get the keys of the dictionaries so a list of dictionaries can be created
    for k in sorted(dict.keys()):
        nl.append({k: []})
        nl_index.append(k)
    # for each item in the original dictionary append the inner dictionaries items to the original dictionaries in the list of dictionaries
    for key, l in dict.items():
        # for each of the items get the keys and values to add them to the list of dictionaries
        for l_key, l_value in l.items():
            nl[nl_index.index(key)][key].append(l_value)
    # return the list of dictionaries
    return nl

# get the reviews and update the mongoDB with the data
def store_reviews(game_name, data, review_type):
    # set the mongoDB instance
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    # set the mongoDB client
    mydb  = myclient['BAX422final']
    # set the database
    mycol = mydb['games']
    # define the filter to use for the mongoDB call
    filter = {'slug': game_name}
    # define the data to update the mongoDB with
    newvalues = {'$set': {review_type: data}}
    # using the filter update the desired mongoDB document with the desired data
    mycol.update_one(filter, newvalues)

# get the review block with the text and the review score
def get_review_blocks(html_doc, reference):
    # using the reference get the correct elements for the reviews
    element = html_doc.select(reference)
    # return the elements which are the review text blocks
    return element

# collect the games to analyze from the RAWG API and store them in a mongoDB database

# make a noise to indicate the program is ready for input
beepy.beep(sound=1)
# get input on if data is needed from the API
if input('Do you want to collect game data from the API(Yes/No): ').lower() == 'yes':
    # combine the API data from 2 pages worth of data from the RAWG API
    combined_data = combine_data_api(2)
    # store the data in the 'games' document database
    store_many_mongodb(combined_data, 'games')
    # for each of the games in the mongoDB get the RAWG game id
    game_ids = [item['id'] for item in get_data_mongo('games', {}, {'id': 1, '_id': 0, 'slug':1})]
    # if there is already a folder labeled 'game_html'
    if 'game_html' in os.listdir():
        # for each game in the 'game_html' folder
        for game in os.listdir('game_html'):
            # open the first page of game html
            game_file = open_html( os.getcwd() + '\\game_html' + '\\' + game + '\\page0.html')
            # collect the user score
            user_review_score = get_text(game_file, 'div[class^="metascore_w user large"]')[0]
            # store the reviews for the users
            store_reviews(game, user_review_score, 'user_review_score')

    # if there is no 'game_html' folder
    else:
        # create a list of the game names and urls
        urls = [(game_name, game_name_url) for game_name, game_name_url in collect_metacritic_urls(game_ids).items()]
        # for each of the urls in the data
        for url in urls:
            # get the html from the url
            game_file = get_html(url[1])
            # get the text reviews for the game
            user_review_score = get_text(game_file, 'div[class^="metascore_w user large"]')
            # store the user reviews in the mongoDB
            store_reviews(url[0], user_review_score[0], 'user_review_score')
            # pause the program so the website doesn't block our IP and we have to find a new way to work around collecting the game review data
            time.sleep(5)

# collect the HTML data
# make a noise to show the program is ready for more input
beepy.beep(sound=1)
if input('Do you want to collect HTML data(Yes/No): ').lower() == 'yes':
    # collect the game ids from the stored mongoDB documents
    game_ids = [item['id'] for item in get_data_mongo('games', {}, {'id': 1, '_id': 0, 'slug':1})]
    # collect the HTML data from metacritic for the critic reviews
    # make a noise to show the program is ready for more input
    beepy.beep(sound=1)
    if input('Do you want to collect Metacritic critic review HTML(Yes/No): ').lower() == 'yes':

        # transform the metacritic urls to be the critic review url
        critic_urls = [(game_name, game_name_url + '/critic-reviews') for game_name, game_name_url in collect_metacritic_urls(game_ids).items()]
        # check if there is a directory to store the critic reviews HTML and if there is no directory create one in the current working directory
        if 'critic_html' not in os.listdir():
            os.mkdir(os.getcwd() + '/critic_html')
        # for each of the games collect the HTML for the critic reviews
        for url in critic_urls:
            # get the critic html
            critic_data = get_html(url[1])
            # save the html to a file
            save_html(critic_data, 'critic_html\\' + re.sub(r"[:\s]", '', url[0]))
            # pause the program a random amount of time so our IP doesn't get blocked
            time.sleep(random.randrange(5,12))

    # collect the HTML data from metacritic for the user reviews
    # make a noise to show the program is ready for more input
    beepy.beep(sound=1)
    if input('Do you want to collect Metacritic user review HTML(Yes/No): ').lower() == 'yes':
        # convert the metacritic url to be the urls for the url for user reviews on a certain page
        user_urls = [(game_name, game_name_url + '/user-reviews?page=') for game_name, game_name_url in collect_metacritic_urls(game_ids).items()]
        # check if there is a directory to store the user reviews HTML and if there is no directory create one in the current working directory
        if 'game_html' not in os.listdir():
            os.mkdir(os.getcwd() + '/game_html')
        # for each of the games collect the HTML for the user reviews
        for url in user_urls:
            # get the HTML for the first page of user reviews
            user_data = get_html(url[1] + str(0))
            # determine how many pages there are
            number_of_pages = get_text(user_data, 'li[class="page last_page"] > a[class="page_num"]')
            # get the name of the current game
            current_game = re.sub(r"[:\s]", '', url[0])
            # check if there is a directory to store the current games reviews HTML and if there is no directory create one in the current working directory
            if current_game not in os.listdir(os.getcwd() + '/game_html'):
                os.mkdir(os.getcwd() + '/game_html/' + current_game)
            # save the first pages HTML data to the appropriate directory
            save_html(user_data, 'game_html\\' + current_game + '\\' + 'page' + '0')
            # pause the program so the IP doesn't get banned
            time.sleep(5)
            # check if there is more than one page based on if there is a returned object from the above check. If the list is empty code will not run and therefore there is only one page of reviews
            if number_of_pages:
                # convert the number of pages into an integer
                number_of_pages = int(number_of_pages[0])
                # for each page of reviews save the HTML to the appropriate directory
                for page in range(1, number_of_pages):
                    user_data = get_html(url[1] + str(page))
                    save_html(user_data, 'game_html\\' + current_game + '\\' + 'page' + str(page))
                    time.sleep(random.randrange(5,12))
            time.sleep(random.randrange(5,12))

# collect the review text for the games and store it in mongoDB
beepy.beep(sound=1)
if input('Do you want to collect review data(Yes/No): ').lower() == 'yes':
    # get a list of all the words in the brown corpus from the nltk package
    words = set(w.lower() for w in brown.words())
    # set the stop words
    stop_words = set(stopwords.words('english'))

    # Collect all the review text for the critic reviews
    # make a noise to show the program is ready for input
    beepy.beep(sound=1)
    if input('Do you want to collect critic review text data(Yes/No):').lower() == 'yes':
        # for each file in the critic_html directory
        for filename in os.listdir('critic_html'):
            # create an empty dictionary entry for the current game
            critic_review_dict = {}
            # open the file
            file_data = open_html('critic_html\\' + filename)
            count = 0
            # for each review on the metacritic critic review page get the review text
            for item in get_review_blocks(file_data, 'li[class^="review critic_review"] div[class="review_section"]'):
                review_text = get_text(item, 'div[class="review_body"]')[0]
                review_score = get_text(item, 'div[class^="metascore"]')[0]
                # tokenize the words in the review so they can be compared with the corpus
                review_word_set = word_tokenize(re.sub('[^\w\s]', '', review_text.strip()), language='english')
                # remove stop words from the review
                review_word_set = [w for w in review_word_set if not w.lower() in stop_words]
                # a list for all the words in the review which are also in the corpus
                approved = []
                # for each word check if it is in the corpus
                for review_word in review_word_set:
                    if review_word in words:
                        # add the approved word to the approved list
                        approved.append(review_word)
                # add the tokenized review to the specific games list of reviews and record the order of the review
                critic_review_dict[str(count)] = {'review_score': review_score,'review_text': approved}
                count = count + 1
            # save the reviews as a part of the overall games table
            store_reviews(re.sub('.html', '', filename), critic_review_dict, 'critic_reviews')

    # collect all the review text for the user reviews
    # make a sound to show the program is ready for more input
    beepy.beep(sound=1)
    if input('Do you want to collect user review text data(Yes/No): ').lower() == 'yes':
        # go through each game directory
        for game_directory in os.listdir('game_html'):
            # set the path
            path = os.getcwd() + '/game_html/'
            # create an empty dictionary to store all of the review text
            count = 0
            # create an empty dictionary for the game
            user_review_dict = {}
            # go through each page of user reviews
            for game_page in os.listdir(path + game_directory):
                # get the html from the stored files
                file_data = open_html(path + game_directory + '/' + game_page)
                # goes through the text for each review
                for item in get_review_blocks(file_data, 'li[class^="review user_review"] div[class="review_section"]'):
                    # gets the text from the review
                    review_text = get_text(item, 'span:not([class^="inline"]), span[class="blurb blurb_expanded"]')
                    # if there is review text
                    if review_text:
                        # store the review text
                        review_text = review_text[0]
                    else:
                        # store an empty string if there is no text
                        review_text = ''
                    # store the score for the reviews
                    review_score = get_text(item, 'div[class^="metascore"]')[0]
                    # get each individual word in the review
                    review_word_set = word_tokenize(re.sub('[^\w\s]', '', review_text.strip()), language='english')
                    # remove stop words from the review
                    review_word_set = [w for w in review_word_set if not w.lower() in stop_words]
                    approved = []
                    # for each word in the review check if it is in the list of 50,000 words in the brown corpus
                    for review_word in review_word_set:
                        # add the word to the approved list
                        if review_word in words:
                            approved.append(review_word)
                    # add the approved words to the appropriate game dictionary at the correct position
                    user_review_dict[str(count)] = {'review_score': review_score, 'review_text': approved}
                    count = count + 1
            # save the reviews as a part of the overall games table
            store_reviews(re.sub('.html', '', game_directory), user_review_dict, 'user_reviews')
# make a sound to show the program is done running
beepy.beep(sound=4)