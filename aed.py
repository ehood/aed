import os
import json
import requests
import compare
import ssdeep
local_dir = './Traffic/'

# { res_id:{}}
# {res_id : {
#               token1 : [] // the tokens in original response
#               token2 : [] // the tokens in the response to the copy of the request we sent.
#             } , ...
# }
res_token_dict = {}
# { req_id :  [ {
#               body : True/False // specify if the token was found in the body of the request (in the params)
#               param_name :      // the param name in which we found the token
#               token_index :     // the token index in the above dictionary
#               res_id :          //the id of the response where the token is found.},... ] , ...
# }
req_dict = {}
cookie = ""


def update_res_token_dict(req_id):
    try:
       data = get_json(req_id)
    except ValueError as ve:
        print "Value Error in Json : ", ve
        return
    try:
        if not data or not data['params']:
            return None
    except Exception as ex:
        print "Exception : ", ex

    for obj in res_token_dict:
        for key, value in data['params'].iteritems():
            i = 0
            flag = False
            for token in res_token_dict[obj]['token1']:
                if token == value:
                    val = {'body': True,
                           'param_name': key,
                           'token_index': i,
                           'res_id': obj}
                    if req_id in req_dict:
                        req_dict[req_id].append(val)
                    else:
                        req_dict[req_id] = [val]
                i += 1

        # TODO - add multiple query params support
        if not flag:
            i = 0
            for token in res_token_dict[obj]['token1']:
                if data['url'].find(token) != -1:
                    val = {'body': False,
                           'param_name': None,
                           'token_index': i,
                           'res_id': obj}
                    req_dict[req_id] = [val]


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
    update_res_token_dict(i)
    try:
        if os.path.isfile(local_dir + str(i) + '/' + str(i) + '_resSecond'):
            res = get_res_from_file(i)
        else:
            res = send_req(i)
            if res is None:
                return
            res = res.content
        compare_response_for_token(res, i)
    except IOError as io:
        print "Error io - req : ", i, " ", io


def round_two(last_req_id):
    flag = False
    tokens = []
    for i in xrange(0, last_req_id):
        if i in req_dict:
            try:
                tokens = get_new_token(i)
                flag = True
                break
            except Exception as ex:
                print "Exception : ", ex
                flag = False
        if flag:
            res = send_request_with_cookie(i, tokens)
        else:
            res = send_request_with_cookie(i, None)
        if res is None:
            continue

        compare_responses_cookie(i, res)


def get_tokens_from_res_dict(res_id, index):
    return res_token_dict[res_id]['token1'][index], res_token_dict[res_id]['token2'][index]


def send_req(req_id):
    data = get_json(req_id)
    if not data:
        return None
    if data['method'] == "GET":
        if req_dict:
            for key in req_dict[req_id]:
                if not req_dict[req_id][key]['body']:
                    id_of_res = req_dict[req_id][key]['res_id']
                    t1, t2 = get_tokens_from_res_dict(id_of_res, req_dict[req_id][key]['token_index'])
                    data['url'] = data['url'].replace(t1, t2)
        r = requests.get(data['url'], headers=data['headers'])
    elif data['method'] == "POST":
        if req_dict:
            for key in req_dict[req_id]:
                if req_dict[req_id][key]['body']:
                    id_of_res = req_dict[req_id][key]['res_id']
                    t1, t2 = get_tokens_from_res_dict(id_of_res, req_dict[req_id][key]['token_index'])
                    data['params'] = data['params'][req_dict[req_id][key]['param_name']].replace(t1,t2)
        r = requests.post(data['url'], headers=data['headers'], data=data['params'])
    return r


def get_new_token(req_id):
    tokens = []
    if req_id not in req_dict:
        return []
    else:
        for item in req_dict[req_id]:
            if item['res_id'] in req_dict:
                t = get_new_token(item['res_id'])
                res_body = send_request_with_new_token(item['res_id'], t).content
                res_body_second = get_res_from_file(item['token_index']['res_id'])
                t1, t2 = compare.find_diff_str(res_body_second, res_body)
                token = t2[item['token_index']]
                tokens.append(token)
            else:
                res_body = send_req(item['res_id']).content
                start_index = res_token_dict[item['token_index']]['start']
                end_index = start_index + len(res_token_dict[item['token_index']]['token1'])
                token = extract_token_from_response(res_body, start_index, end_index)
                tokens.append(token)
        return tokens


def extract_token_from_response(text, start_index, end_index):
    return text[start_index:end_index]


def send_request_with_cookie(req_id, new_tokens):
    data = get_json(req_id)
    if not data:
        return None
    if not ('cookie' in data['headers']):
        return None
    data['headers']['cookie'] = cookie
    if data['method'] == "GET":
        j = 0
        if req_dict:
            for key in req_dict[req_id]:
                if not req_dict[req_id][key]['body']:
                    id_of_res = req_dict[req_id][key]['res_id']
                    t1, t2 = get_tokens_from_res_dict(id_of_res, req_dict[req_id][key]['token_index'])
                    data['url'] = data['url'].replace(t1, new_tokens[j])
                j += 1
        r = requests.get(data['url'], headers=data['headers'])
    elif data['method'] == "POST":
        j = 0
        if req_dict:
            for key in req_dict[req_id]:
                if req_dict[req_id][key]['body']:
                    id_of_res = req_dict[req_id][key]['res_id']
                    t1, t2 = get_tokens_from_res_dict(id_of_res, req_dict[req_id][key]['token_index'])
                    data['params'] = data['params'][req_dict[req_id][key]['param_name']].replace(t1, new_tokens[j])
                j += 1
        r = requests.post(data['url'], headers=data['headers'], data=data['params'])
    return r


def send_request_with_new_token(req_id, new_tokens):
    data = get_json(req_id)
    if not data:
        return None
    if data['method'] == "GET":
        j = 0
        if req_dict:
            for key in req_dict[req_id]:
                if not req_dict[req_id][key]['body']:
                    id_of_res = req_dict[req_id][key]['res_id']
                    t1, t2 = get_tokens_from_res_dict(id_of_res, req_dict[req_id][key]['token_index'])
                    data['url'] = data['url'].replace(t1, new_tokens[j])
                j+=1
        r = requests.get(data['url'], headers=data['headers'])
    elif data['method'] == "POST":
        j = 0
        if req_dict:
            for key in req_dict[req_id]:
                if req_dict[req_id][key]['body']:
                    id_of_res = req_dict[req_id][key]['res_id']
                    t1, t2 = get_tokens_from_res_dict(id_of_res, req_dict[req_id][key]['token_index'])
                    data['params'] = data['params'][req_dict[req_id][key]['param_name']].replace(t1, new_tokens[j])
                j += 1
        r = requests.post(data['url'], headers=data['headers'], data=data['params'])
    return r


def compare_responses_cookie(res_id, res):
    if not os.path.isfile(local_dir + str(res_id) + '/' + str(res_id) + '_resSecond'):
        print "req ", res_id, 'ok'
        return
    with open(local_dir + str(res_id) + '/' + str(res_id) + '_resSecond', 'r') as response:
        res_copy = response.read()
        s1 = ssdeep.hash(res_copy, encoding='utf-8')
    s2 = ssdeep.hash(res.content, encoding='utf-8')
    var = ssdeep.compare(s1, s2)

    if var > 95:
        print "req ", res_id, 'passed'
    elif var > 80:
        print "req ", res_id, 'suspicious'
    else:
        print "req ", res_id, 'ok'


# compare the response with the response that we have stored as response of req_id
def compare_response_for_token(res, req_id):

    res_copy = get_res1_from_file(req_id)
    if not res_copy:
        return
    try:
        st, end = compare.find_hidden_input(res, res_copy)
        if not st and not end:
            st, end = compare.find_diff_str(res, res_copy)
            if st:
                res_token_dict[req_id] = {
                                      'token1': st,
                                      'token2': end
                }
        else:
            res_token_dict[req_id] = {
                                  'token1': [st],
                                  'token2': [end]
            }
    except Exception as ex:
        print "Error in compare.py : ", ex, " Req : ", req_id
    try:
        if not os.path.isfile(local_dir + str(req_id) + '/' + str(req_id) + '_resSecond'):
            with open(local_dir + str(req_id) + '/' + str(req_id) + '_resSecond', 'wb') as body:
                body.write(res)
    except IOError as io:
        print "Error : ", io


def get_res_from_file(_id):
    try:
        with open(local_dir + str(_id) + '/' + str(_id) + '_resSecond', 'rb') as r:
            res = r.read()
            return res
    except IOError as io:
        print "res ", _id, " IO ERROR - ", io
        return None


def get_res1_from_file(_id):
    try:
        with open(local_dir + str(_id) + '/' + str(_id) + '_res', 'rb') as r:
            res = r.read()
            return res
    except IOError as io:
        print "res ", _id, " IO ERROR - ", io
        return None


def get_json(_id):
    try:
        with open(local_dir + str(_id) + '/' + str(_id) + '_req.json', 'r') as fp:
            data = json.load(fp)
        return data
    except IOError as io:
        print "req ", _id, " IO ERROR - ", io
        return None


def start(last_req_id):
    round_one(last_req_id)
    round_two(last_req_id)
