import os
import json
import requests
import compare
import ssdeep
local_dir = './Traffic/'

# { res_id:{}}
token_dict = {}
cookie = ""


def is_token_in_dict(req_id):
    try:
        with open(local_dir + str(req_id) + '/' + str(req_id) + '_req.json', 'r') as fp:
            data = json.load(fp)
    except IOError as io:
        print "Error IO req_id : ", req_id
        print io
    except ValueError as ve:
        print "Value Error in Json : ", ve
    try:
        if not data or not data['params']:
            return None
    except Exception as ex:
        print "Exception : ", ex

    for obj in token_dict:
        for key, value in data['params'].iteritems():
            if value.find(token_dict[obj]['token1']) != -1:
                token_dict[obj]['req_id'] = req_id
                token_dict[obj]['body'] = True
                token_dict[obj]['param_name'] = key
                return obj
        if data['url'].find(token_dict[obj]['token1']) != -1:
            token_dict[obj]['req_id'] = req_id
            token_dict[obj]['body'] = False
            token_dict[obj]['param_name'] = None
            return obj


def round_one(last_req_id):
    for i in xrange(0, last_req_id):
        print "req ", i
        try:
            round_one_step_i(i)
        except requests.ConnectionError as ce:
            print "Connection Error Retry", ce
            try:
                round_one_step_i(i)
                print "Retry worked"
            except Exception as ex:
                print "Exception in round 1, req id ", i, " : ", ex


def round_one_step_i(i):
    id_of_res = is_token_in_dict(i)
    try:
        if os.path.isfile(local_dir + str(i) + '/' + str(i) + '_resSecond'):
            with open(local_dir + str(i) + '/' + str(i) + '_resSecond', 'rb') as r:
                res = r.read()
        else:
            if not id_of_res:
                res = send_req(i, None)
                if not res:
                    return
                res = res.content
            else:
                res = send_req(i, id_of_res)
                if not res:
                    return
                res = res.content
        compare_response_for_token(res, i)
    except IOError as io:
        print "Error io - req : ", i, " ", io


def round_two(last_req_id):
    flag = False
    for i in xrange(0, last_req_id):
        for key, value in token_dict.iteritems():
            if value['req_id'] == i:
                try:
                    token = get_new_token(key)
                    flag = True
                    break
                except Exception as ex:
                    print "Exception : ", ex

        if flag:
            res = send_request_with_cookie(i, token)
            if res is None:
                continue
        else:
            res = send_request_with_cookie(i, None)
            if res is None:
                continue
        compare_responses_cookie(i, res)


def send_req(req_id, id_of_res):
    with open(local_dir + str(req_id) + '/' + str(req_id) + '_req.json', 'r') as fp:
        data = json.load(fp)
    if not data:
        return None
    if data['method'] == "GET":
        if id_of_res:
            if not data['body']:
                data['url'] = data['url'].replace(token_dict[id_of_res]['token1'], token_dict[id_of_res]['token2'])
        r = requests.get(data['url'], headers=data['headers'])
    elif data['method'] == "POST":
        if id_of_res:
            if data['body']:
                data['params'][token_dict[id_of_res]['param_name']] = data['params'][token_dict[id_of_res]['param_name']].replace(token_dict[id_of_res]['token1'],token_dict[id_of_res]['token2'])
        r = requests.post(data['url'], headers=data['headers'], data=data['params'])
    return r


def get_new_token(res_id):
    for key in token_dict:
        if token_dict[key]['req_id'] == res_id:
            start_index = token_dict[key]['start']
            end_index = start_index + len(token_dict[key]['token1'])
            # MISSING IMPLEMENTION
            res_body = send_request_with_new_token(token_dict[key]['req_id'],get_new_token).content
            return extract_token_from_response(res_body, start_index, end_index)


def extract_token_from_response(text, start_index, end_index):
    return text[start_index:end_index]


def send_request_with_cookie(req_id, new_token):
    with open(local_dir + str(req_id) + '/' + str(req_id) + '_req.json', 'r') as fp:
        data = json.load(fp)
    if not data:
        return None
    if not ('cookie' in data['headers']):
        return None
    data['headers']['cookie'] = cookie
    if data['method'] == "GET":
        if new_token:
            if req_id in token_dict:
                if not token_dict[req_id]['body']:
                    data['url'] = data['url'].replace(token_dict[req_id]['token1'], new_token)
        r = requests.get(data['url'], headers=data['headers'])
    elif data['method'] == "POST":
        if req_id:
            if new_token:
                if req_id in token_dict:
                    if token_dict[req_id]['body']:
                        data['params'][token_dict[req_id]['param_name']] = data['params'][token_dict[req_id]['param_name']].replace(token_dict[req_id]['token1'], new_token)
        r = requests.post(data['url'], headers=data['headers'], data=data['params'])
    return r


def send_request_with_new_token(req_id, new_token):
    with open(local_dir + str(req_id) + '/' + str(req_id) + '_req.json', 'r') as fp:
        data = json.load(fp)
    if data['method'] == "GET":
        if new_token:
            if not data['body']:
                data['url'] = data['url'].replace(token_dict[req_id]['token1'], new_token)
        r = requests.get(data['url'],headers=data['headers'])
    elif data['method'] == "POST":
        if req_id:
            if data['body']:
                data['params'][token_dict[req_id]['param_name']] = data['params'][token_dict[req_id]['param_name']].replace(token_dict[req_id]['token1'], new_token)
        r = requests.post(data['url'], headers=data['headers'], data=data['params'])
    return r


def compare_responses_cookie(res_id, res):
    with open(local_dir + str(res_id) + '/' + str(res_id) + '_resSecond', 'r') as response:
        res_copy = response.read()
        s1 = ssdeep.hash(res_copy, encoding='utf-8')
    s2 = ssdeep.hash(res.content, encoding='utf-8')
    var = ssdeep.compare(s1, s2)

    if var > 95:
        print "req ", res_id, 'passed'
    else:
        print "req ", res_id, 'ok'


# compare the response with the response that we have stored as response of req_id
def compare_response_for_token(res, req_id):
    try:
        with open(local_dir + str(req_id) + '/' + str(req_id)+'_res', 'r') as response:
            res_copy = response.read()
            try:
                st, end = compare.find_hidden_input(res, res_copy)
                if not st and not end:
                    st, end = compare.find_diff_str(res, res_copy)
            except Exception as ex:
                print "Error in compare.py : ", ex, " Req : ", req_id
    except IOError as io:
        print "Error : ", io

    if st and end:
        token_dict[req_id] = {'req_id': '',
                              'body': False,
                              'token1': res_copy[st:end],
                              'token2': res[st:end],
                              'start': st}
    try:
        if not os.path.isfile(local_dir + str(req_id) + '/' + str(req_id) + '_resSecond'):
            with open(local_dir + str(req_id) + '/' + str(req_id) + '_resSecond', 'wb') as body:
                body.write(res)
    except IOError as io:
        print "Error : ", io


def start(last_req_id):
    round_one(last_req_id)
    round_two(last_req_id)

