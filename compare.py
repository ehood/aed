__author__ = 'ehood'


end_chars = [',', ';', '.', r"'", "}", ':', '>', r'"', '\n', '\r']
start_chars = [',', ';', '.', r"'", '\n', '\r', ':', '<', '{', r'"']


# the function should get the responses without the headers.
def find_diff_str(response1, response2):
    indexes = []
    i = 0  # len(response1)
    while i < len(response1) and i < len(response2):
        if response1[i] == response2[i]:
            i += 1
        else:
            j = i
            while i < len(response1) and response1[i] not in end_chars:
                i += 1
            while j >= 0 and response1[j] not in start_chars:
                j -= 1
            t1 = response1[(j+1): i]
            t2 = response2[(j+1): i]
            wrong_char = False
            for f in end_chars+start_chars:
                if t1.find(f) != -1 or t2.find(f) != -1:
                    wrong_char = True
                    break
            if not wrong_char:
                indexes.append((j+1, i))

    return indexes


def find_hidden_input(response1, response2):
    if response1 and response2:
        index_of = response1.find(r'input type="hidden"')
        while index_of != -1:
            y = 0
            x = response1.find(r'value="', index_of)
            j = x
            if x != -1:
                y += response1.find(r'"', x+7)
                if y != -1:
                    while x < y:
                        if response1[x] != response2[x]:
                            return (j+7), y
                        x += 1
            index_of = response1.find(r'input type="hidden"', index_of+1)
    return None, None
