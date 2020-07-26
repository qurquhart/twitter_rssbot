from flask import render_template, flash, redirect, url_for, request, session, jsonify, json
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, RssForm, RssRemove, PostSettings
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Rss, Post
from werkzeug.urls import url_parse
from datetime import datetime, timedelta, date
import feedparser
from app.juice import lemonade, timeget, metapull
import math
from app.twitter_api import *
import re


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    # rss = User.rsssources(current_user)

    # set holding list len() to result of refresh_period/post_freq

    # posts = User.postsfromrss(current_user).order_by(Post.auto_post_datetime.asc())
    postoutput = math.ceil(current_user.auto_post_refresh / current_user.auto_post_interval)
    # posts = User.postsfromrss(current_user).order_by(Post.auto_post_datetime.asc())
    posts = Post.query.filter_by(author=current_user, postedtw=False).order_by(Post.auto_post_datetime.asc())
    for post in posts:
        # print(post.url)
        # print(post.meta_data)
        if not post.meta_data:
            post.meta_data = metapull(post.url)
    db.session.commit()

    # holdinglist = []
    # for a in aposts:
    #     holdinglist.append(a.__dict__)

    # posts = lemonade(holdinglist, 'rss_id')

    # meta_posts = []




    # print(posts)

    next_refresh = ""
    if current_user.last_refresh is not None:
        next_refresh = current_user.last_refresh + current_user.auto_post_refresh



    return render_template('index.html', title='Home', next_refresh=next_refresh, posts=posts, user=current_user, postoutput=postoutput)


@app.route('/history', methods=['GET'])
@login_required
def history():
    posts = User.postsfromrss(current_user).order_by(Post.auto_post_datetime.desc())
    return render_template('history.html', posts=posts, user=current_user)


@app.route('/rss', methods=['GET', 'POST'])
@login_required
def rss():
    rssform = RssForm()
    removerss = RssRemove()

    if rssform.validate_on_submit():
        try:
            d = feedparser.parse(rssform.post.data)
            postget = d
            rssurls = Rss(url=rssform.post.data, posts=postget, author=current_user)
            # author=current_user

            db.session.add(rssurls)
            db.session.commit()
            flash('added rss source')
            session['url'] = url_for('rss')
            return redirect(url_for('create_posts'))
        except all:
            flash('invalid rss')
            return redirect(url_for('rss'))

        return redirect(url_for('rss'))

    rssurls = User.rsssources(current_user)
    return render_template('rss.html', title='RSS', rssurls=rssurls, form=rssform, form2=removerss)


@app.route('/schedule_posts', methods=['GET', 'POST'])
@login_required
def schedule_posts():
    print(f'User attempting to schedule posts - {datetime.utcnow()}')

    posts = Post.query.filter_by(author=current_user, postedtw=False)
    holdinglist = []

    for a in posts:
        holdinglist.append(a.__dict__)

    print(f'Posts sent to lemonade: {len(holdinglist)}')

    sortedposts = lemonade(holdinglist, 'rss_id')

    print(f'Posts received from lemonade: {len(sortedposts)}')

    last_post_time = None
    last_post = Post.query.filter_by(author=current_user, postedtw=True).order_by(
        Post.auto_post_datetime.desc()).first()
    if last_post is not None:
        if last_post.auto_post_datetime > datetime.utcnow() - current_user.auto_post_interval:
            last_post_time = last_post.auto_post_datetime

    print(f'last post: {last_post_time}')

    good_times = timeget(current_user.auto_post_active_start,
                         current_user.auto_post_active_end,
                         current_user.auto_post_interval,
                         len(sortedposts),
                         last_post_time
                         )

    for count, n in enumerate(range(len(sortedposts))):
        postid = sortedposts[count]['id']
        getpost = Post.query.filter_by(user_id=current_user.id, id=postid).first()

        getpost.auto_post_datetime = good_times[count]

    db.session.commit()

    flash(f'Scheduled {len(sortedposts)} posts.')

    if 'url' in session:
        return redirect(session['url'])
    return redirect(url_for('index'))

@app.route('/hashtags/post', methods=['GET', 'POST'])
@login_required
def hashtagspost():
    json = request.form.to_dict()

    hashtags = []
    for a in json:
        hashtags.append(json[a])

    hash_list = []
    count = 0

    while count < len(hashtags):
        hash_dict = {"search": hashtags[count], "hashtag": hashtags[count+1]}
        # hash_dict.update({"search": hashtags[count]})
        # hash_dict.update({"hashtag": hashtags[count+1]})
        hash_list.append(hash_dict)
        count += 2

    print(hash_list)
    # user = User.query.filter_by(id=current_user.id)
    current_user.hashtag_dict = hash_list
    db.session.commit()
    return json

@app.route('/hashtags', methods=['GET', 'POST'])
@login_required
def hashtags():
    if not current_user.hashtag_dict:
        tags = [{"search":"",
                "hashtag":""}]
    else:
        tags = current_user.hashtag_dict

    # tags = [{"search":"one",
    #        "hashtag":"#one"},
    #        {"search": "two",
    #         "hashtag": "#two"}
    #        ]
    # tags = str(tags1)
    # flash(current_user.hashtag_dict)

    return render_template('hashtags.html', tags=tags)


@app.route('/create_posts', methods=['GET', 'POST'])
@login_required
def create_posts():
    print(f'User attempting to create posts - {datetime.utcnow()}')
    # refresh rss sources
    rss_get = User.rsssources(current_user)
    rssurls = []
    for url in rss_get:
        rssurls.append(url.url)

    print(f'Collected RSS urls: {rssurls}')

    rss_get.delete()
    db.session.commit()
    print(f'Deleted RSS urls for {current_user}')
    for rss in rssurls:
        # print(rss)

        try:
            postget = feedparser.parse(rss)
            rssurls = Rss(url=rss, posts=postget, author=current_user)
            # author=current_user

            db.session.add(rssurls)
            db.session.commit()
            print(f'Added RSS source: {rss}')
        except all:
            flash('invalid rss')
            return redirect(url_for('rss'))


    # delete current posts old
    Post.query.filter_by(author=current_user, postedtw=False).delete()
    db.session.commit()
    print('Removed unposted posts.')
    # set last refresh time
    current_user.last_refresh = datetime.utcnow()
    print(f'Set last refresh: {datetime.utcnow()}')
    # replace them with new posts

    posts = Rss.query.filter_by(author=current_user)

    history = Post.query.filter_by(author=current_user, postedtw=True)

    post_history = []

    # print('shit')
    # print(post_history)

    for post in history:
        # print(post.url)
        post_history.append(post.url)

    post_output = math.ceil(current_user.auto_post_refresh / current_user.auto_post_interval)
    created_posts = 0
    posts_in_history = 0
    # create posts from rss feed
    print('')
    print('---------------------------Creating Posts--------------------------------')
    for rssurl in posts:
        for x in rssurl.posts.entries:
            if 1 == 1:
                link = x['link']
                print(f'Attempt: {link}')
                if link not in post_history:
                    hashtags = current_user.hashtag_dict
                    body = x['title']
                    print(f'history check OK')
                    taglist = []
                    count = 0
                    tags = ""
                    if hashtags is not None:
                        while count < len(hashtags):
                            if re.search(f"({hashtags[count]['search']})\W", str(body), re.IGNORECASE):
                                taglist.append(hashtags[count]['hashtag'])
                            count += 1
                        print(f'hashtags: {taglist}')

                        tags = ""

                        for tag in taglist:
                            tags = f'{tag} ' + tags

                    # meta_data = metapull(link)

                    # meta_data = "none"

                    # post length checker
                    # len() body + tags + 23 for link
                    # if too long shorten body with "..."
                    # reference character count in tweet display to show shortening

                    tweet_len = len(body) + len(tags) + 23


                    if len(tags) + 23 > 280:
                        flash('hashtags too long')

                    else:
                        print('hashtag length OK')
                        if tweet_len > 270:
                            print('tweet long')
                            flash('Tweet too long, text shortened.')
                            body_short = body
                            # tweet_short = len(body_short) + len(tags) + 23
                            leftover_body = 270 - len(tags) - 23
                            while len(body_short) > leftover_body:
                                body_short = body_short[:-1]
                            makepost = Post(body=body_short+"...", rss_id=rssurl.id, url=link,
                                            author=current_user, hashtags=tags,
                                            character_count=tweet_len)
                            db.session.add(makepost)
                            db.session.commit()
                            created_posts += 1
                        else:
                            print('tweet length OK')
                            makepost = Post(body=body, rss_id=rssurl.id, url=link,
                                            author=current_user, hashtags=tags,
                                            character_count=tweet_len)
                            db.session.add(makepost)
                            print('Created Post')
                            print('')
                            db.session.commit()
                            created_posts += 1
                else:
                    print(f'POST IN HISTORY: {link}')
                    posts_in_history += 1


    flash(f"Created {created_posts} Posts")
    if posts_in_history > 0:
        flash(f"Skipped {posts_in_history} posts.  Already Posted.")
    print(f"-------------------Created {created_posts} Posts-----------------------")
    return redirect(url_for('schedule_posts'))


@app.route('/deletepost', methods=['POST'])
@login_required
def deletepost():
    json = request.form.to_dict()
    print(json['id'])
    Post.query.filter_by(id=json['id']).delete()
    db.session.commit()
    return json


@app.route('/setposted', methods=['POST'])
@login_required
def setposted():
    json = request.form.to_dict()
    print(json['id'])
    post = Post.query.filter_by(id=json['id']).first()
    print(post.postedtw)
    post.postedtw = True
    db.session.commit()
    return json


@app.route('/delete_rss/<string:uid>', methods=['POST'])
@login_required
def delete_rss(uid):
    Post.query.filter_by(rss_id=uid).delete()
    Rss.query.filter_by(id=uid).delete()

    db.session.commit()
    flash(f"Removed Source")
    return redirect(url_for('rss'))


@app.route('/do_not_post/<string:pid>', methods=['POST'])
@login_required
def do_not_post(pid):
    post = Post.query.filter_by(id=pid).first()
    if post.do_not_post is True:
        post.do_not_post = False
        db.session.commit()
        flash(f"Post ID#{pid} will be posted.")
    else:
        post.do_not_post = True
        db.session.commit()
        flash(f"Post ID#{pid} will not be posted.")
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        userinfo = User.query.filter_by(username=form.username.data).first()
        if userinfo is None or not userinfo.check_password(form.password.data):
            flash('Invalid username of password')
            return redirect(url_for('login'))
        login_user(userinfo, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(url_for('index'))

    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # noinspection PyArgumentList
        userinfo = User(username=form.username.data, email=form.email.data)
        userinfo.set_password(form.password.data)
        db.session.add(userinfo)
        db.session.commit()
        flash('Registration Successful')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/giveaway', methods=['GET', 'POST'])
def giveaway():
    posts = twitter_posts(current_user.twitter_key, current_user.twitter_secret)
    return render_template('giveaway.html', title='Giveaway', posts=posts, tweet=None)


@app.route('/giveaway/tweet/<tweetid>', methods=['GET', 'POST'])
@login_required
def giveaway_tweet(tweetid):
    key, secret = current_user.twitter_key, current_user.twitter_secret

    tweet = tweet_details(key, secret, tweetid)
    posts = twitter_posts(key, secret)
    retweet_search = f"filter:nativeretweets {tweet.text}"
    retweets = twitter_search(key, secret, retweet_search)
    retweet_user_list = []

    for tweets in retweets:
        flash(tweets.user.screen_name)
        flash(current_user.twitter_user_info.screen_name)

        friendship = twitter_isfriend(key,
                                      secret,
                                      current_user.twitter_user_info.screen_name,
                                      tweets.user.screen_name)
        flash(friendship[0].followed_by)
        if friendship[0].followed_by is True:
            retweet_user_list.append(tweets.user.screen_name)
            flash(f'{tweets.user.screen_name} is following me')
    #    else:
    #        flash('not following me')

    # flash(retweets.user.screen_name)

    return render_template('giveaway.html', title='Giveaway', posts=posts, tweet=tweet, retweeters=retweet_user_list)


@app.route('/process', methods=['POST'])
def process():
    json = request.form.to_dict()
    tz = {'tz': json['tz']}

    aoffset = re.search("(GMT)\s*([^\s]+)", tz['tz'])
    offset = re.search("[^GMT]\s*([^\s]+)", aoffset.group(0))

    print(offset.group(0))
    # print(int(offset.group(0))-20)
    session['tz'] = offset.group(0)
    return session['tz']


@app.route('/settings/<username>', methods=['GET', 'POST'])
@login_required
def user(username):
    userinfo = User.query.filter_by(username=username).first()
    form = PostSettings()
    postoutput = math.ceil(current_user.auto_post_refresh/current_user.auto_post_interval)

    if 'submit-interval' in request.form:
        delta = timedelta(minutes=form.interval.interval.data)
        current_user.auto_post_interval = delta
        db.session.commit()
        flash('interval submitted')
        # tell the schedule post page what url the request came from
        session['url'] = url_for('user', username=current_user.username)
        return redirect(url_for('create_posts', username=username))
    if 'submit-refresh' in request.form:
        delta = timedelta(minutes=form.refresh.interval.data)
        current_user.auto_post_refresh = delta
        db.session.commit()
        flash('refresh submitted')
        session['url'] = url_for('user', username=current_user.username)
        return redirect(url_for('create_posts', username=username))
    if 'submit-duration' in request.form:
        form_start = form.duration.time_start.data
        form_end = form.duration.time_end.data

        timezone = session['tz']

        tz_delta = timedelta(hours=int(timezone[1:-2]), minutes=int(timezone[-2:]))

        if form_start < form_end:
            if timezone[:1] == '-':
                # subtract delta
                start = (datetime.combine(datetime.now(), form_start) + tz_delta).time()
                end = (datetime.combine(datetime.now(), form_end) + tz_delta).time()
                current_user.auto_post_active_start = start
                current_user.auto_post_active_end = end
                db.session.commit()
                flash(f'post time submitted tz = {datetime.utcnow() - datetime.now()}'
                      f'  browser time {request.args.get("date")} startutc {start}')
            elif timezone[:1] == '+':
                # add delta
                start = (datetime.combine(datetime.now(), form_start) - tz_delta).time()
                end = (datetime.combine(datetime.now(), form_end) - tz_delta).time()
                current_user.auto_post_active_start = start
                current_user.auto_post_active_end = end
                db.session.commit()
                flash(f'post time submitted tz = {datetime.utcnow() - datetime.now()}'
                      f'  browser time {request.args.get("date")} startutc {start}')
            else:
                flash('error wrong time format from JS')
        else:
            flash(f'invalid post times - end time is before start time - start {form_start} end {form_end}')
            return redirect(url_for('user', username=username))

        session['url'] = url_for('user', username=current_user.username)
        return redirect(url_for('schedule_posts', username=username))


    elif request.method == 'GET':
        timezone = session['tz']
        tz_delta = timedelta(hours=int(timezone[1:-2]) ,minutes=int(timezone[-2:]))

        form.interval.interval.data = round(current_user.auto_post_interval.seconds/60)

        if timezone[:1] == '-':
            form.duration.time_start.data = (datetime.combine(date.today(),
                                                              current_user.auto_post_active_start) - tz_delta).time()
            form.duration.time_end.data = (datetime.combine(date.today(),
                                                            current_user.auto_post_active_end) - tz_delta).time()
        elif timezone[:1] == '+':
            form.duration.time_start.data = (datetime.combine(date.today(),
                                                              current_user.auto_post_active_start) + tz_delta).time()
            form.duration.time_end.data = (datetime.combine(date.today(),
                                                            current_user.auto_post_active_end) + tz_delta).time()

        form.refresh.interval.data = round(current_user.auto_post_refresh.seconds / 60)
    dt = datetime.utcnow()

    if not current_user.hashtag_dict:
        tags = [{"search":"",
                "hashtag":""}]
    else:
        tags = current_user.hashtag_dict

    return render_template('user.html', tags=tags, user=userinfo, form=form, postoutput=postoutput, dt=dt)




@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('changes saved')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile', form=form)


@app.route('/follow/<username>')
@login_required
def follow(username):
    userinfo = User.query.filter_by(username=username).first()
    if userinfo is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if userinfo == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('user', username=username))
    current_user.follow(userinfo)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('user', username=username))


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    userinfo = User.query.filter_by(username=username).first()
    if userinfo is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if userinfo == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('user', username=username))
    current_user.unfollow(userinfo)
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('user', username=username))


consumer_key = 'VYS7wJC5VFMF42Jh4QgnU3fKA'
consumer_secret = 'DgviLln4UPTJLvWxEyWcPOontSs9uygCtdRdLsCeZieLfnz4HM'
callback = 'http://127.0.0.1:5000/callback'


@app.route('/auth')
@login_required
def auth():
    twitter_auth = tweepy.OAuthHandler(consumer_key, consumer_secret, callback)
    url = twitter_auth.get_authorization_url()
    session['request_token'] = twitter_auth.request_token
    return redirect(url)


@app.route('/callback')
def twitter_callback():
    request_token = session['request_token']
    del session['request_token']

    twitter_auth = tweepy.OAuthHandler(consumer_key, consumer_secret, callback)
    twitter_auth.request_token = request_token
    verifier = request.args.get('oauth_verifier')
    twitter_auth.get_access_token(verifier)
    session['token'] = (twitter_auth.access_token, twitter_auth.access_token_secret)

    # tokens = User(twitter_key=auth.access_token, twitter_secret=auth.access_token_secret)
    # current_user.twitter_key = auth.access_token
    # current_user.twitter_secret = auth.access_token_secret
    # db.session.add(tokens)
    # db.session.commit()
    token, token_secret = session['token']
    current_user.twitter_key = token
    current_user.twitter_secret = token_secret

    current_user.twitter_user_info = twitter_me(current_user.twitter_key, current_user.twitter_secret)

    db.session.commit()

    return redirect(url_for('index'))
    # return redirect(url_for('writetoken'))


@app.route('/removetoken')
@login_required
def removetoken():
    # token, token_secret = session['token']
    token, token_secret = None, None
    current_user.twitter_key = token
    current_user.twitter_secret = token_secret
    db.session.commit()

    return redirect(url_for('index'))
