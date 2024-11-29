from collections.abc import Iterable
import os
import pandas as pd

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
