from bs4 import BeautifulSoup
from requests import TooManyRedirects
import re
import requests
from datetime import datetime
import os
import pandas as pd
import regex as re
import json

def get_url_response(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print('Aborted as response code is not 200')
            return None
    except error as e:
        print(f'[request {url} failed] : {e}')
        return None
    return json.loads(response.content)

#------------------------------------- CRITIC ---------------------------------------------------
def get_critic_page_init(movie_name):
    movie_name = re.sub(r"[^a-zA-Z]{1,}", "_", movie_name).lower()
    if movie_name[-1] == '_':
        movie_name = movie_name[:-1]
    # print(f'Try to get response from https://www.rottentomatoes.com/m/{movie_name}/reviews')
    response = requests.get(f'https://www.rottentomatoes.com/m/{movie_name}/reviews')
    soup = BeautifulSoup(response.content, 'html.parser')
    critics = soup.find_all('div',class_ = 'review-row')

    # find movie id
    rtid = soup.find('script',{"id":"mps-page-integration"}).contents[0].replace('|','').strip()
    rtid = [x for x in rtid.split(',') if 'rtid' in x][0].strip().split(':')[-1][1:-1]

    load_btn = soup.find_all('rt-button',{'data-loadmoremanager':"btnLoadMore:click"})
    if load_btn:
        hasNextPage = True
    else:
        hasNextPage = False
    return critics,rtid, hasNextPage

def get_critic_page_follow(movie_id,start_token = None):
    url = f'https://www.rottentomatoes.com/napi/movie/{movie_id}/reviews/all?after={start_token}%3D%3D&pageCount=20'
    # print(f'Using url:{url}')
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print('Aborted as response code is not 200')
            return None
    except error as e:
        print(f'[request {url} failed] : {e}')
    return json.loads(response.content)

def get_review_data_soup(critics):
    # find disp_name
    try:
        critics_reviewer = critics.find_all('div',class_ = 'reviewer-name-and-publication')
        disp_name = critics_reviewer[0].find( class_ = "display-name").contents[0].strip()
    except Exception as e:
        disp_name = ''
        print(f'failed to get review text:{e}')
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
        
    critics_score_str = [x for x in critics.find('p',class_ = 'original-score-and-url').contents if not hasattr(x,'contents')]
    def try_score_map(x):
        try:
            score = x.replace('|','').strip()
            return score
        except:
            return None
    # find score         
    try:
        review_score = [score for score in list(map(try_score_map,critics_score_str)) if bool(score)]
    except Exception as e:
        print(f'failed to get review score:{e}')
        review_score = ''
    if review_score:
        review_score = review_score[0].split()[-1].strip()
    else:
        review_score = 'Not found'
    # find sentiment
    try:
        review_sentiment = critics.find('score-icon-critics').attrs['sentiment']
    except Exception as e:
        print(f'failed to get review sentiment:{e}')
        review_sentiment = None
    # find review text
    try:
        review_text = critics.find('p', class_ = 'review-text').contents[0]
    except Exception as e:
        print(f'failed to get review text:{e}')
        review_text = ''   
    if review_text:
        review_text = review_text
    else:
        review_text = 'Not Found'
        
    return [disp_name,review_date,review_score,review_sentiment,review_text,1]

def get_review_data_json(json_rvw_data, page = None):
    def get_json_info(jsn,key):
        if key in jsn.keys():
            return jsn[key]
        else:
            return None
    disp_name = get_json_info(json_rvw_data,'criticName')
    review_date = get_json_info(json_rvw_data, 'creationDate')
    review_date = datetime.strptime(json_rvw_data['creationDate'], '%b %d, %Y')
    review_score = get_json_info(json_rvw_data, 'originalScore')
    review_sentiment = get_json_info(json_rvw_data, 'scoreSentiment')
    review_text = get_json_info(json_rvw_data, 'quote')

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
    init_pg_critics, rtid, hasNextPage = get_critic_page_init(movie_title)
    # ingest page1 data
    print(f'Scraping page{1} of {movie_title}')
    for row in range(len(init_pg_critics)):
        review_row = init_pg_critics[row]
        rtid = get_critic_page_init(movie_title)[1]
        review_row_data = get_review_data_soup(review_row)
        df = append_review_df(df, movie_title, rtid, *review_row_data)
    # end if no load more btn found
    if not hasNextPage:
        return df
    
    # other page
    is_first_loop = True
    while True:   
        if is_first_loop:
            start_token = 'MQ'
            pg = 1
        
        try:
        
            res = get_critic_page_follow(movie_id = rtid,start_token = start_token)
            if not res: # the movie has no more review page
                break
            
            print(f'Scraping page{pg} of {movie_title} using start key = {start_token}')
            for row in res['reviews']:
                review_row_data = get_review_data_json(row, page = pg)
                df = append_review_df(df, movie_title, rtid, *review_row_data)
            is_first_loop = False # Disable init var
            # check if has next page
            if 'hasNextPage' in res['pageInfo'].keys():
                print(res['pageInfo']['hasNextPage'])
                if not res['pageInfo']['hasNextPage']:
                    return df   
            
            previous_start_token = start_token
            start_token = res['pageInfo']['endCursor'].replace('==','')
            print(f'Found next page token {start_token}')   
            pg += 1
        except Exception as e:
            print(f'Error getting review of id:{rtid} on page{pg},   {e}')    
            try:
                if previous_start_token == start_token:
                    break
            except Exception as e:
                break
    return df