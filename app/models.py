from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login
from hashlib import md5
from datetime import timedelta, time

# these are database models, sqlite


# update process
# add or remove fields to a class
# flask db migrate
# flask db upgrade
#

# self referential relationship
followers = db.Table('followers',
                     db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
                     db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
                     )


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    rss = db.relationship('Rss', backref='author', lazy='dynamic')
    post = db.relationship('Post', backref='author', lazy='dynamic')
    twitter_key = db.Column(db.String(120))
    twitter_secret = db.Column(db.String(120))
    twitter_user_info = db.Column(db.PickleType)
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    auto_post_interval = db.Column(db.Interval(), default=timedelta(minutes=60))
    auto_post_active_start = db.Column(db.Time, default=time(12, 00, 00))
    auto_post_active_end = db.Column(db.Time, default=time(2, 00, 00))
    auto_post_refresh = db.Column(db.Interval(), default=timedelta(minutes=240))
    hashtag_dict = db.Column(db.PickleType)
    # LAST REFRESH
    last_refresh = db.Column(db.DateTime)


    def _repr__(self):
        return '<User {}'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
                followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    def rsssources(self):
        return Rss.query.filter_by(user_id=self.id)

    def postsfromrss(self):
        return Post.query.filter_by(user_id=self.id)

    def uid(self):
        return User.query.filter_by(user_id=self.id)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    postedfb = db.Column(db.Boolean(), default=False)
    postedtw = db.Column(db.Boolean(), default=False)
    do_not_post = db.Column(db.Boolean())
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rss_id = db.Column(db.Integer)
    auto_set_post_time = db.Column(db.Boolean(), default=True)
    url = db.Column(db.String(140))
    hashtags = db.Column(db.String(140))
    auto_post_datetime = db.Column(db.DateTime)
    meta_data = db.Column(db.PickleType)
    character_count = db.Column(db.Integer)
    # user_set_post_time =
    # if else statement to prioritize auto_set_time and user_set_time
    # iterate through rss pickle to create posts
    # can delete all posts from specified rss by searching for rss.id
    # then shuffle the data: list from each rss.id and cycle through setting post time
    # set post order by adjusting post time
    # auto_post settings in User.model

    def __repr__(self):
        return '<Post {}>'.format(self.body)


class Rss(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(140))
    posts = db.Column(db.PickleType)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post {}>'.format(self.posts)


@login.user_loader
def load_user(userid):
    return User.query.get(int(userid))
