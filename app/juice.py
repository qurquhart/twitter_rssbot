import itertools as it
from datetime import datetime, time
from bs4 import BeautifulSoup
import requests

def lemonade(input_list, key):
    # ---------- SEPARATE INPUT (rss2) LIST BY SOURCE INTO MULTIPLE LISTS -------------
    print('-----------------lemonde start----------------------')
    # get all source values
    sourcenum = []
    for a in input_list:
        print(f'post dict content: {str(a)[:50]}...')
        rssidstr = ""
        for b in str(a[f'{key}']):
            # print(f'b: {b}')
            rssidstr += b
        print(f'rssid: {rssidstr}')
        sourcenum.append(rssidstr)

    print(f'RSS ID input list: {sourcenum}')

    # create list of sources for
    source = sorted(list(set(sourcenum)))

    # for each source in the list of sources, append
    # all items from that source to the output list
    output = []
    for o in source:
        output.append((list(filter(lambda sources: sources[f'{key}'] == int(o), input_list))))
    # print(f'output: {output}')

    # ---------- SEPARATE INPUT (rss2) LIST BY SOURCE INTO MULTIPLE LISTS -------------

    # round robin by source
    zipped = (map(list, it.zip_longest(*output)))

    # combine into one complete list while remove None values from zip_longest
    flat_list = []
    for sublist in zipped:
        for item in sublist:
            if item is not None:
                flat_list.append(item)
    # the glorious output
    rssidoutput = []
    for post in flat_list:
        rssidoutput.append(post['rss_id'])
    print(f'RSS ID output list: {rssidoutput}')
    print('-----------------lemonde end----------------------')
    return flat_list


def timeget(rangestart, rangeend, interval, postcount, last_post_time):

    if last_post_time:
        now = last_post_time
    else:
        now = datetime.utcnow()

    start = datetime.combine(now, rangestart).time()
    end = datetime.combine(now, rangeend).time()
    time_list = []
    count = 1

    # create times until the list is the same length as the amount of posts

    # if start - end is positive then multiple days

    # post time between START-11:59:59 | OR | 0:00:00-END
    # APPEND

    def time_seconds(time):
        t = str(time)
        (h, m, s) = t.split(':')
        result = int(h) * 3600 + int(m) * 60 + int(s[:2])
        return result

    while len(time_list) < postcount:
        # if its between the start and end hour add the time to the list


        if time_seconds(start) - time_seconds(end) < 0:
            if start < (now + interval * count).time() < end:
                time_list.append(now + (interval * count))
                count += 1
            else:
                count += 1
        else:
            if time(0,0,0,0) < (now + interval * count).time() < end or\
                    start < (now + interval * count).time() < time(23, 59, 59, 59):
                time_list.append(now + (interval * count))
                count += 1
            else:
                count += 1

    return time_list

def timeget1(rangestart, rangeend, interval, postcount):
    now = datetime.utcnow()
    start = datetime.combine(now, rangestart).time()
    end = datetime.combine(now, rangeend).time()
    time_list = []
    count = 1

    # create times until the list is the same length as the amount of posts

    # if start - end is positive then multiple days

    # post time between START-11:59:59 | OR | 0:00:00-END
    # APPEND

    def time_seconds(time):
        t = str(time)
        (h, m, s) = t.split(':')
        result = int(h) * 3600 + int(m) * 60 + int(s[:2])
        return result

    while len(time_list) < postcount:
        # if its between the start and end hour add the time to the list


        if time_seconds(start) - time_seconds(end) < 0:
            if start < (now + interval * count).time() < end:
                time_list.append(now + (interval * count))
                count += 1
            else:
                count += 1
        else:
            if time(0,0,0,0) < (now + interval * count).time() < end or\
                    start < (now + interval * count).time() < time(23, 59, 59, 59):
                time_list.append(now + (interval * count))
                count += 1
            else:
                count += 1

    return time_list


def metapull(link):
    meta = []
    try:
        url = requests.get(link)
        soup = BeautifulSoup(url.text, 'html.parser')
        a = soup.find('meta', {'property': "og:title"})['content']
        b = soup.find('meta', {'property': "og:image"})['content']
        c = soup.find('meta', {'property': "og:description"})['content']
        meta.append(b)
        meta.append(a)
        meta.append(c)
    except Exception as ex:
        print(ex)

    return meta