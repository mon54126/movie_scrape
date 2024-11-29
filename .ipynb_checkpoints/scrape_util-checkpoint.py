from collections.abc import Iterable
import os
import pandas as pd
import json
from requests import TooManyRedirects
import requests

def get_url_response(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print('Aborted as response code is not 200')
            return None
    except Exception as e:
        print(f'[request {url} failed] : {e}')
        return None
    return json.loads(response.content)

def map_empty_string_to_null(x):
    if isinstance(x, Iterable):
        return [None if (not i and type(i) == str) else i for i in x]
    else:
        if not x:
            return None
        else:
            return x

def get_value_from_dict_key(keys,d):
    r = []
    for k in keys:
        if k in d.keys():
            r.append(d[k])
        else:
            r.append(None)
    return r

def concat_df_from_dir(dir):
    f_dir = os.path.join(os.getcwd(),dir)
    f_list = os.listdir(f_dir)
    f_path = [os.path.join(f_dir,fname) for fname in f_list if 'csv' in fname.lower()]
    df_union = pd.concat([pd.read_csv(fpath) for fpath in f_path], ignore_index = True)
    return df_union
