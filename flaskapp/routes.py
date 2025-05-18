from flask import render_template, flash, redirect, url_for, request
from flaskapp import app, db
from flaskapp.models import BlogPost, IpView, Day, UkData
from flaskapp.forms import PostForm
import datetime

import pandas as pd
import json
import plotly
import plotly.express as px
import plotly.graph_objects as go


# Route for the home page, which is where the blog posts will be shown
@app.route("/")
@app.route("/home")
def home():
    # Querying all blog posts from the database
    posts = BlogPost.query.all()
    return render_template('home.html', posts=posts)


# Route for the about page
@app.route("/about")
def about():
    return render_template('about.html', title='About page')


# Route to where users add posts (needs to accept get and post requests)
@app.route("/post/new", methods=['GET', 'POST'])
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = BlogPost(title=form.title.data, content=form.content.data, user_id=1)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post', form=form)


# Route to the dashboard page
@app.route('/dashboard')
def dashboard():
    days = Day.query.all()
    df = pd.DataFrame([{'Date': day.id, 'Page views': day.views} for day in days])

    fig = px.bar(df, x='Date', y='Page views')

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('dashboard.html', title='Page views per day', graphJSON=graphJSON)


@app.before_request
def before_request_func():
    day_id = datetime.date.today()  # get our day_id
    client_ip = request.remote_addr  # get the ip address of where the client request came from

    query = Day.query.filter_by(id=day_id)  # try to get the row associated to the current day
    if query.count() > 0:
        # the current day is already in table, simply increment its views
        current_day = query.first()
        current_day.views += 1
    else:
        # the current day does not exist, it's the first view for the day.
        current_day = Day(id=day_id, views=1)
        db.session.add(current_day)  # insert a new day into the day table

    query = IpView.query.filter_by(ip=client_ip, date_id=day_id)
    if query.count() == 0:  # check if it's the first time a viewer from this ip address is viewing the website
        ip_view = IpView(ip=client_ip, date_id=day_id)
        db.session.add(ip_view)  # insert into the ip_view table

    db.session.commit()  # commit all the changes to the database


@app.route('/uk_dashboard')
def uk_dashboard():
    uk_data = UkData.query.all()

    uk_df = pd.DataFrame([
        {
            'Constituency': uk.constituency_name,
            'Turnout2019': uk.Turnout19,
            'Students': uk.c11FulltimeStudent,
            'Retired': uk.c11Retired,
            'Female': uk.c11Female,
            'HomeOwned': uk.c11HouseOwned
        }
        for uk in uk_data
    ])

    # --- Bottom 5 ---
    bottom5 = uk_df.nsmallest(5, 'Turnout2019')
    fig_low = px.bar(
        bottom5,
        x='Constituency',
        y='Turnout2019',
        title='Bottom 5: Lowest Voter Turnout (2019)',
        color='Turnout2019',
        color_continuous_scale='Blues'
    )
    fig_low.update_layout(xaxis_tickangle=-45)

    # --- Top 5 ---
    top5 = uk_df.nlargest(5, 'Turnout2019')
    fig_high = px.bar(
        top5,
        x='Constituency',
        y='Turnout2019',
        title='Top 5: Highest Voter Turnout (2019)',
        color='Turnout2019',
        color_continuous_scale='Greens'
    )
    fig_high.update_layout(xaxis_tickangle=-45)

    # --- Demographics Bottom 5 ---
    demo_cols = ['Students', 'Retired', 'Female', 'HomeOwned']
    bottom_demo = bottom5[demo_cols].mean().reset_index()
    bottom_demo.columns = ['Demographic', 'Average']

    fig_demo_bottom = px.bar(
        bottom_demo,
        x='Demographic',
        y='Average',
        title='Demographic Averages in Bottom 5 Turnout Constituencies',
        color='Average',
        color_continuous_scale='Purples'
    )

    # --- Demographics Top 5 ---
    top_demo = top5[demo_cols].mean().reset_index()
    top_demo.columns = ['Demographic', 'Average']

    fig_demo_top = px.bar(
        top_demo,
        x='Demographic',
        y='Average',
        title='Demographic Averages in Top 5 Turnout Constituencies',
        color='Average',
        color_continuous_scale='Oranges'
    )

    # Encode all to JSON
    graphs = {
        "low": json.dumps(fig_low, cls=plotly.utils.PlotlyJSONEncoder),
        "high": json.dumps(fig_high, cls=plotly.utils.PlotlyJSONEncoder),
        "demo_low": json.dumps(fig_demo_bottom, cls=plotly.utils.PlotlyJSONEncoder),
        "demo_high": json.dumps(fig_demo_top, cls=plotly.utils.PlotlyJSONEncoder),
    }

    return render_template("uk_dashboard.html", title="UK Electoral Dashboard", **graphs)
