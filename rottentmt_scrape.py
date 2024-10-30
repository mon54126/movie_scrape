from bs4 import BeautifulSoup
from requests import TooManyRedirects
import re
import requests
from datetime import datetime
import os
import pandas as pd

def get_critic_page_init(movie_name):
    movie_name = movie_name.lower()
    response = requests.get(f'https://www.rottentomatoes.com/m/{movie_name.replace(' ','_')}/reviews')
    soup = BeautifulSoup(response.content, 'html.parser')
    critics = soup.find_all('div',class_ = 'review-row')

    # find movie id
    rtid = soup.find('script',{"id":"mps-page-integration"}).contents[0].replace('|','').strip()
    rtid = [x for x in rtid.split(',') if 'rtid' in x][0].strip().split(':')[-1][1:-1]
    return critics,rtid

def get_critic_page_follow(movie_id,start_token = None):
    url = f'https://www.rottentomatoes.com/napi/movie/{movie_id}/reviews/all?after={start_token}%3D%3D&pageCount=20'
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print('Aborted as response code is not 200')
            return
    except error as e:
        print(f'[request {url} failed] : {e}')
    return json.loads(response.content)
    
def get_review_data_soup(critics):
    critics_reviewer = critics.find_all('div',class_ = 'reviewer-name-and-publication')
    disp_name = critics_reviewer[0].find( class_ = "display-name").contents[0].strip()
    # find review_date
    critics_score_content = [x for x in critics.find('p',class_ = 'original-score-and-url').contents if hasattr(x,'contents')]
    def try_dt_map(x):
        try:
            dt = datetime.strptime(x.contents[0], '%b %d, %Y')
            return dt
        except:
            return None
    review_date = [dt for dt in list(map(try_dt_map,critics_score_content)) if bool(dt)]
    if review_date:
        review_date = review_date[0]
    else:
        review_date = 'Not found'
        
    # find score
    critics_score_str = [x for x in critics.find('p',class_ = 'original-score-and-url').contents if not hasattr(x,'contents')]
    def try_score_map(x):
        try:
            score = x.replace('|','').strip()
            return score
        except:
            return None
    review_score = [score for score in list(map(try_score_map,critics_score_str)) if bool(score)]
    if review_score:
        review_score = review_score[0].split()[-1].strip()
    else:
        review_score = 'Not found'

    # find sentiment
    review_sentiment = critics.find('score-icon-critics').attrs['sentiment']
    # find review text
    review_text = critics.find('p', class_ = 'review-text').contents[0]
    if review_text:
        review_text = review_text
    else:
        review_text = 'Not Found'
        
    return [disp_name,review_date,review_score,review_sentiment,review_text,1]

def get_review_data_json(json_rvw_data, page = None):
    disp_name = json_rvw_data['criticName']
    review_date = datetime.strptime(json_rvw_data['creationDate'], '%b %d, %Y')
    review_score = json_rvw_data['originalScore']
    review_sentiment = json_rvw_data['scoreSentiment']
    review_text = json_rvw_data['quote']
    return [disp_name,review_date,review_score,review_sentiment,review_text,page]

def get_movie_reviews(movie_title):
    # create dataframe
    df = pd.DataFrame({'movie_title':[],
                       'movie_id':[],
                       'reviewer_name':[],
                       'review_date':[],
                       'review_score':[],
                       'review_sentiment':[],
                       'review_text':[],
                       'on_page':[]
                        })
    def append_review_df(df, movie_title, movie_id, reviewer_name, review_date, review_score, review_sentiment, review_text, on_page):
        df_to_append = pd.DataFrame({'movie_title':[movie_title],
                                     'movie_id':[movie_id],
                                     'reviewer_name':[reviewer_name],
                                     'review_date':[review_date],
                                     'review_score':[review_score],
                                     'review_sentiment':[review_sentiment],
                                     'review_text':[review_text],
                                     'on_page':[on_page]
                                    })
        return df._append(df_to_append, ignore_index = True)
    # page1 init
    init_pg_critics, rtid = get_critic_page_init('hocus_pocus')
    # ingest page1 data
    for i in range(len(init_pg_critics)):
        review_row = init_pg_critics[i]
        rtid = get_critic_page_init('hocus_pocus')[1]
        review_row_data = get_review_data_soup(review_row)
        df = append_review_df(df, movie_title, rtid, *review_row_data)
    # other page
    get_critic_page_follow(movie_id,start_token = None)
    return df