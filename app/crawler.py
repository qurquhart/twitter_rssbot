from app.models import *
from app import scheduler
from app.twitter_api import twitter_post
import feedparser
from app.juice import lemonade, timeget
import math
import re


def post_crawler():
    crawl_log = open("crawlerlog.txt", "a+")
    print('--------------------------Crawl Start----------------------------')
    print('')
    print(f'Server Time: {datetime.utcnow()}')
    crawl_log.write('--------------------------Crawl Start----------------------------\r\n')
    crawl_log.write('\r\n')
    crawl_log.write(f'Server Time: {datetime.utcnow()}\r\n')
    try:
        all_users = User.query.all()
        print(f'List of Users: {all_users}')
        crawl_log.write(f'List of Users: {all_users}\r\n')


        for user in all_users:

            print(f'Checking user {user.username} for eligible posts.')
            crawl_log.write(f'Checking user {user.username} for eligible posts.\r\n')
            posts = Post.query.filter_by(author=user, postedtw=False)
            unpostable = 0

# ######### posting tweets start
            for post in posts:
                if post.auto_post_datetime is not None:

                    if post.auto_post_datetime < datetime.utcnow():

                        tweet = post.body+" "+post.hashtags+" "+post.url
                        f = open("tweetlog.txt", "a+")

                        try:
                            twitter_post(user.twitter_key, user.twitter_secret, tweet)
                            print(f'POSTED TWEET: {tweet}')
                            crawl_log.write(f'POSTED TWEET: {tweet}\r\n')
                            f.write(f"{datetime.utcnow()} - USER:{user.username} POSTED TWEET: {tweet} \r\n")

                        except Exception as ex:
                            print(f'Tweet Failed: {ex}')
                            crawl_log.write(f'Tweet Failed: {ex}\r\n')
                            f.write(f"{datetime.utcnow()} - USER:{user.username} TWEET FAILED: {ex} USER:{user} TWEET: {tweet} \r\n")

                        f.close()
                        post.postedtw = True
                        db.session.commit()

                    else:
                        unpostable += 1
# ######### posting tweets end

            print(f'Tweets not ready to post: {unpostable}')
            print('')
            crawl_log.write(f'Tweets not ready to post: {unpostable}\r\n')
            crawl_log.write('\r\n')

# ######### refresh/create posts start
            if user.last_refresh is not None:
                if user.last_refresh + user.auto_post_refresh < datetime.utcnow():
                    # #################################################################################
                    # create posts
                    print(f'Refreshing posts for {user}.')
                    crawl_log.write(f'Refreshing posts for {user}.\r\n')
                    rss_get = Rss.query.filter_by(user_id=user.id)
                    rssurls = []
                    for url in rss_get:
                        rssurls.append(url.url)

                    print(f'RSS URLs: {rssurls}')
                    crawl_log.write(f'RSS URLs: {rssurls}\r\n')

                    rss_get.delete()
                    db.session.commit()

                    for rss in rssurls:
                        print(f'Trying URL: {rss}')
                        crawl_log.write(f'Trying URL: {rss}\r\n')

                        try:
                            postget = feedparser.parse(rss)
                            rssurls = Rss(url=rss, posts=postget, author=user)
                            # author=current_user

                            db.session.add(rssurls)
                            db.session.commit()
                            print('Success')
                            crawl_log.write('Success\r\n')
                        except all as ex:
                            print(f'Fail: {ex}')
                            crawl_log.write(f'Fail: {ex}\r\n')

                    # delete current posts old
                    Post.query.filter_by(author=user, postedtw=False).delete()
                    db.session.commit()

                    # set last refresh time
                    user.last_refresh = datetime.utcnow()

                    # replace them with new posts
                    posts = Rss.query.filter_by(author=user)

                    history = Post.query.filter_by(author=user, postedtw=True)

                    post_history = []

                    for post in history:
                        post_history.append(post.url)

                    post_output = math.ceil(user.auto_post_refresh / user.auto_post_interval)
                    created_posts = 0
                    # create posts from rss feed
                    for rssurl in posts:
                        for x in rssurl.posts.entries:
                            # if created_posts < post_output:
                            if 1 == 1:
                                link = x['link']

                                if link not in post_history:
                                    hashtags = user.hashtag_dict
                                    body = x['title']

                                    taglist = []
                                    count = 0
                                    tags = ""
                                    if hashtags is not None:
                                        while count < len(hashtags):
                                            if re.search(f"({hashtags[count]['search']})\W", str(body), re.IGNORECASE):
                                                taglist.append(hashtags[count]['hashtag'])
                                            count += 1
                                        print(taglist)
                                        crawl_log.write(f'{taglist}\r\n')

                                        tags = ""

                                        for tag in taglist:
                                            tags = f'{tag} ' + tags

                                    tweet_len = len(body) + len(tags) + 23

                                    if len(tags) + 23 > 280:
                                        print('hashtags too long')
                                        crawl_log.write('hashtags too long\r\n')

                                    else:

                                        if tweet_len > 270:
                                            print('Tweet too long, text shortened.')
                                            crawl_log.write('Tweet too long, text shortened.\r\n')
                                            body_short = body
                                            leftover_body = 270 - len(tags) - 23
                                            while len(body_short) > leftover_body:
                                                body_short = body_short[:-1]
                                            makepost = Post(body=body_short + "...", rss_id=rssurl.id, url=link,
                                                            author=user, hashtags=tags,
                                                            character_count=tweet_len)
                                            db.session.add(makepost)
                                            db.session.commit()
                                            created_posts += 1
                                        else:
                                            makepost = Post(body=body, rss_id=rssurl.id, url=link,
                                                            author=user, hashtags=tags,
                                                            character_count=tweet_len)
                                            db.session.add(makepost)
                                            db.session.commit()
                                            created_posts += 1

# ######### refresh/create posts end

# ######### schedule posts start

                    print('------------------Scheduling Posts--------------------')
                    crawl_log.write('------------------Scheduling Posts--------------------\r\n')

                    posts = Post.query.filter_by(author=user, postedtw=False)
                    holdinglist = []

                    for a in posts:
                        holdinglist.append(a.__dict__)

                    print(f'Posts sent to lemonade: {len(holdinglist)}')
                    crawl_log.write(f'Posts sent to lemonade: {len(holdinglist)}\r\n')

                    sortedposts = lemonade(holdinglist, 'rss_id')

                    print(f'Posts received from lemonade: {len(sortedposts)}')
                    crawl_log.write(f'Posts received from lemonade: {len(sortedposts)}\r\n')

                    last_post_time = None
                    last_post = Post.query.filter_by(author=user, postedtw=True).order_by(
                        Post.auto_post_datetime.desc()).first()
                    if last_post is not None:
                        if last_post.auto_post_datetime > datetime.utcnow() - user.auto_post_interval:
                            last_post_time = last_post.auto_post_datetime

                    print(f'last post: {last_post_time}')
                    crawl_log.write(f'last post: {last_post_time}\r\n')

                    good_times = timeget(user.auto_post_active_start,
                                         user.auto_post_active_end,
                                         user.auto_post_interval,
                                         len(sortedposts),
                                         last_post_time
                                         )

                    for count, n in enumerate(range(len(sortedposts))):
                        postid = sortedposts[count]['id']
                        getpost = Post.query.filter_by(user_id=user.id, id=postid).first()

                        getpost.auto_post_datetime = good_times[count]

                    db.session.commit()

                    print(f'scheduled posts {len(sortedposts)} time list len {len(good_times)}')
                    crawl_log.write(f'scheduled posts {len(sortedposts)} time list len {len(good_times)}\r\n')

# ######### schedule posts end

    except Exception as ex:
        print(f'CRAWL FAILURE: {ex}')
    print('60 seconds...')
    print('')
    print('--------------------------Crawl End----------------------------')
    print('')
    crawl_log.write('60 seconds...\r\n')
    crawl_log.write('\r\n')
    crawl_log.write('--------------------------Crawl End----------------------------\r\n')
    crawl_log.write('\r\n')

# ######### crawler end



# start crawler job
scheduler.add_job(id='Post Crawler', func=post_crawler, trigger='interval', seconds=60)
scheduler.start()

