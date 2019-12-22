from subprocess import call
from datetime import datetime
import os
import pandas as pd
from sty import fg, rs
import time
import csv
import json
import re
import sys
import requests
import shutil

start_time = time.time()
headers_Get = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:49.0) Gecko/20100101 Firefox/49.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

html_tags = {
    'knowledge_panel': 'kp-blk knowledge-panel',
    'claimed': "Own this business?",
    'name': "kno-ecr-pt PZPZlf gsmt",
    'summary': "kc:/local:one line summary",
    'stars': "kc:/collection/knowledge_panels/local_reviewable:star_score",
    'comments': "t-h6pVaOIWfNg",
    'web_review': "kc:/location/location:third_party_aggregator_ratings",
    'phone': 'LrzXr zdqRlf kno-fv',
    # 'days': "kc:/location/location:hours",
    'address': "kc:/location/location:address",
    'website': "IzNS7c duf-h",
    'gmap': "rhsl4 rhsmap3col",
    'visiting': "kc:/local:plan your visit"
}

html_regexes = {
    'name': '<span>(.*)</span>',
    'summary': '<span class="YhemCb">(.*?)</span>',
    'stars': 'aria-label="(.*?)"',
    'comments': '<span>(.*)</span>',
    # 'web_review': 'aria-label="(.*?)"',
    # 'web_review': 'href="(.*?)"',
    'web_review': '(.*)',
    'phone': '<span>(.*?)</span>',
    'hours': '<td>(.*)</td>',
    'address': '<span class="LrzXr">(.*)</span>',
    'website': 'href="(.*?)"',
    'gmap': 'data-url="(.*?)"',
    'visiting': '<b>(.*)</b>'
}

# days = ["Sunday", "Monday", "Tuesday",
#         "Wednesday", "Thursday", "Friday", "Saturday"]

csv_data = 'results.csv'
csv_data_true = 'results_true.csv'
csv_data_false = 'results_false.csv'
good_res = 0
bad_res = 0

EDITOR = os.environ.get('EDITOR') if os.environ.get('EDITOR') else 'vim'


def current_time():
    return datetime.now().strftime('%Y-%m-%d-%H-%M')


def google(q):
    s = requests.Session()
    q = '+'.join(q.casefold().replace(
        '&', ' and ').replace("'", ' ').replace('!', '').replace('é', 'e').split())
    url = 'https://www.google.com/search?q=' + q + '&ie=utf-8&oe=utf-8'
    r = s.get(url, headers=headers_Get)
    return r.text


def get_string_after_tag(string, tag, regex, distance):
    if(tag not in string):
        return None

    index = string.find(tag)
    substr = string[index: index+distance]
    if re.search(regex, substr):
        return re.search(regex, substr).group(1)
    else:
        return None


def get_details(query):
    html_results = google(query)
    results = {'query': query}
    has_knowledge_panel = html_tags['knowledge_panel'] in html_results
    # print(html_results)

    if(has_knowledge_panel):
        results['query'] = query.replace(
            '&', ' and ').replace("'", ' ').replace('!', '')
        results['exists'] = True

        results['name'] = get_string_after_tag(
            html_results, html_tags['name'], html_regexes['name'], 500)

        results['claimed'] = html_tags['claimed'] not in html_results

        summary = get_string_after_tag(
            html_results, html_tags['summary'], html_regexes['summary'], 600)
        if(summary):
            results['summary'] = summary

        stars = get_string_after_tag(
            html_results, html_tags['stars'], html_regexes['stars'], 500)
        if(stars):
            results['stars'] = stars.split(":")[1].split(" sur")[0]

        comments = get_string_after_tag(
            html_results, html_tags['comments'], html_regexes['comments'], 500)
        if(comments):
            results['comments'] = comments.split("\xa0avis")[0]

        web_review = get_string_after_tag(
            html_results, html_tags['web_review'], html_regexes['web_review'], 2500)
        if(web_review):
            web_review_all = re.findall(
                '(?:href=[\'"])([:/.A-z?<_&\s=>0-9;-]+)', web_review)
            web_review_1 = web_review_all[0]
            results['web_review_1'] = web_review_1
            if len(web_review_all) > 1:
                web_review_2 = web_review_all[1]
                results['web_review_2'] = web_review_2

        phone_number = get_string_after_tag(
            html_results, html_tags['phone'], html_regexes['phone'], 200)
        if(phone_number):
            results['phone_number'] = phone_number

        address = get_string_after_tag(
            html_results, html_tags['address'], html_regexes['address'], 1000)
        if(address):
            results['address'] = address

        website = get_string_after_tag(
            html_results, html_tags['website'], html_regexes['website'], 200)
        if(website):
            results['website'] = website.split("/?")[0]

        gmap = get_string_after_tag(
            html_results, html_tags['gmap'], html_regexes['gmap'], 1000)
        if(gmap):
            # results['gmap'] = gmap
            gmap_lat = re.findall("\/@(-?[\d\.]*)", gmap)
            gmap_lng = re.findall("\/@[-?\d\.]*\,([-?\d\.]*)", gmap)
            results['gmap_lat'] = gmap_lat[0]
            results['gmap_lng'] = gmap_lng[0]

        visiting = get_string_after_tag(
            html_results, html_tags['visiting'], html_regexes['visiting'], 500)
        if(visiting):
            results['visiting'] = visiting

        # if html_tags['days'] in html_results:
        #     hours_index = html_results.find(html_tags['days'])
        #     hours_substr = html_results[hours_index: hours_index+2000]
        #     for day in days:
        #         results['{}_hours'.format(day)] = get_string_after_tag(
        #             hours_substr, day, html_regexes['hours'], 50)

    else:
        results['exists'] = False

    return results


if __name__ == "__main__":
    with open(sys.argv[1], newline='') as csvfile:
        with open(csv_data, 'w', newline='') as results:
            reader = csv.reader(csvfile)
            fieldnames = [
                'query',
                'exists',
                'name',
                'summary',
                'phone_number',
                'address',
                'website',
                'web_review_1',
                'web_review_2',
                'claimed',
                'stars',
                'comments',
                'visiting',
                'gmap_lat',
                'gmap_lng',
                # "Friday_hours", "Saturday_hours", "Sunday_hours", "Monday_hours", "Tuesday_hours", "Wednesday_hours", "Thursday_hours"
            ]
            writer = csv.DictWriter(results, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                fetch = get_details(u"  ".join(row))
                if(fetch['exists'] == True):
                    writer.writerow(fetch)
                    print(fg.green, reader.line_num,
                          row[0], fetch['exists'], fg.rs)
                else:
                    fetch = get_details(u"  ".join(row))
                    writer.writerow(fetch)
                    print(fg.li_cyan, "AGAIN!", reader.line_num,
                          row[0], fetch['exists'], fg.rs)
                    if(fetch['exists'] == False):
                        print(fg.red, "... NOPE!!!", fg.rs)

        # CLEAN FILES!
        with open(csv_data, 'r') as inp, open(csv_data_false, 'w') as out:
            writer = csv.writer(out)

            for row in csv.reader(inp):
                if row[1] != "True":
                    writer.writerow(row)

        with open(csv_data, 'r') as inp, open(csv_data_true, 'w') as out:
            writer = csv.writer(out)

            for row in csv.reader(inp):
                if row[1] != "False":
                    writer.writerow(row)

        df = pd.read_csv(csv_data_false)
        # df = df.drop(df.loc[:, 'exists':'gmap_lng'].columns,  axis=1)
        df = df.drop(df.iloc[:, 1:14].columns, axis=1)
        df.to_csv(csv_data_false, header=False, index=False)

        # GET THE COUNT!
        print('')
        print(" 🌈   🦄   💨")
        print('')
        with open(csv_data_true) as f:
            total = sum(1 for line in f)
            good_res = total-1
            print(fg.li_green, "😎   total good data: ", total-1, fg.rs)

        with open(csv_data_false) as f:
            total = sum(1 for line in f)
            bad_res = total
            print(fg.li_red, "😭   total bad data: ", total, fg.rs)
            print('')


# COPY FILES INTO TIMESTAMPS FOLDER IF NEEDED
if(good_res > 0):
    os.mkdir(os.path.join('./', str(current_time())))
    shutil.copy(csv_data,  str(current_time()))
    shutil.copy(csv_data_false,  str(current_time()))
    shutil.copy(csv_data_true,  str(current_time()))


# REPORT
mybad = (bad_res * 100)/(good_res + bad_res)
elapsed_time = time.time() - start_time
print(fg.li_yellow, "🤖   BTW! Done in: ", time.strftime(
    "%H:%M:%S", time.gmtime(elapsed_time)), " with ", "{0:.2f}".format(round(mybad, 2)), "% ", "errors", fg.rs)


try:
    input_ = raw_input
except NameError:
    input_ = input


def query_yes_no(question, default=False):
    yes_list = ["yes", "y"]
    no_list = ["no", "n"]

    default_dict = {
        None: "[y/n]",
        True: "[Y/n]",
        False: "[y/N]",
    }

    default_str = default_dict[default]
    prompt_str = "%s %s " % (question, default_str)

    while True:
        choice = input_(prompt_str).lower()

        if not choice and default is not None:
            return default
        if choice in yes_list:
            return True
        if choice in no_list:
            return False

        notification_str = "Please respond with 'y' or 'n'"
        print(notification_str)


q1 = fg.li_yellow + " 🤖   Do you want to open " + \
    csv_data_false + " inside " + EDITOR + " ?" + fg.rs
qq = fg.li_yellow + " 🤖   Bye..." + fg.rs

print('')
edit_false_data = query_yes_no(q1)
if edit_false_data == True:
    call([EDITOR, csv_data_false])

elif edit_false_data == False:
    print(qq)
    quit
