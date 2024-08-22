from flask import Flask, flash,render_template, request, session, redirect, url_for, jsonify
import pyrebase
import time
import re
from markupsafe import Markup
from flask import send_file
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import pandas as pd


app = Flask(__name__)
app.secret_key = "your_secret_key"

config = {
    "apiKey": "AIzaSyBSTU81m0XTKYkYz8z303qA6QkexeaXRqU",
    "authDomain": "flaskpro-94895.firebaseapp.com",
    "databaseURL": "https://flaskpro-94895-default-rtdb.firebaseio.com",
    "projectId": "flaskpro-94895",
    "storageBucket": "flaskpro-94895.appspot.com",
    "messagingSenderId": "664244820588",
    "appId": "1:664244820588:web:7775f2f60d2e8ab3411649"
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()

# Sample admin credentials
ADMIN_USERNAME = "raghu12@gmail.com"
ADMIN_PASSWORD = "12345678"


def strip_tags(text):
    # Use a regular expression to remove HTML tags
    return re.sub(r'<[^>]+>', '', text)

# Register the custom filter with the Flask app
app.jinja_env.filters['strip_tags'] = strip_tags

@app.route('/')
def index():
    user_data = get_current_user_data()
    blog_posts = fetch_blog_posts()
    events = fetch_events()
    return render_template('index.html', events=events, user_data=user_data, blog_posts=blog_posts)




@app.route('/admin/home')
@app.route('/admin/home/<option>')
def admin_home(option='home'):
    if session['admin'] == True:
        if option == 'users':
            data = {'users':fetch_users()}

        elif option == 'events':
            data = {'events': fetch_events()}

        elif option == 'contacts':
            data = {'contacts': fetch_contacts()}

        elif option == 'home':
            data = {'users': fetch_users(), 'events': fetch_events()}  # Default: Fetch both users and events
    return render_template('admin_home.html', data=data, option=option)



def fetch_contacts():
    contacts = []
    contact_data = db.child('contacts').get().val()  # Assuming 'contacts' is your Firebase node
    if contact_data:
        for contact_id, contact_info in contact_data.items():
            contacts.append({'contact_id': contact_id, **contact_info})
    return contacts

def fetch_blog_posts():
    blog_posts = []
    blog_data = db.child('blogs').get().val()
    if blog_data:
        for post_id, post_info in blog_data.items():
            blog_posts.append({'post_id': post_id, **post_info})
    return blog_posts


def fetch_users():
    users = []
    user_data = db.child('users').get().val()
    if user_data:
        for user_id, user_info in user_data.items():
            users.append({'user_id': user_id, 'name': user_info.get('email', ''),'address':user_info.get('address',''),'mobile_no':user_info.get('mobile_no',''),'college':user_info.get('college',''),'profile_img':user_info.get('profile_image_url','')})
    return users


def fetch_events():
    events = []
    events_data = db.child('events').get().val()
    if events_data:
        for event_id, event_info in events_data.items():
            events.append({'event_id': event_id, **event_info})



    # Optionally, sort events by start_datetime
    events = sorted(events, key=lambda x: x['start_datetime'])

    return events

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        mobile_no = request.form['mobile_no']
        college = request.form['college']
        dob = request.form['dob']
        address = request.form['address']
        profile_image = request.files['profile_image']
        image_url = None

        if profile_image:
            # Save the profile image to Firebase Storage
            storage = firebase.storage()
            image_path = f"profile_images/{email}_{profile_image.filename}"
            storage.child(image_path).put(profile_image)
            image_url = storage.child(image_path).get_url(None)


        try:
            user = auth.create_user_with_email_and_password(email, password)
            add_user_to_database(user['localId'], email, name, mobile_no, college, dob, address, image_url)
            session['user'] = user['idToken']
            return redirect(url_for('profile'))
        except Exception as e:

            return render_template('error.html', error=f"Error uploading profile image: {e}")
    return render_template('signup.html')



@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' in session:
        user = auth.get_account_info(session['user'])
        user_id = user['users'][0]['localId']
        user_data = db.child('users').child(user_id).get().val()
        if request.method == 'POST':
            name = request.form['name']
            mobile_no = request.form['mobile_no']
            college = request.form['college']
            dob = request.form['dob']
            address = request.form['address']
            profile_image = request.files['profile_image']


            update_user_details(user_id, name, mobile_no, college, dob, address, profile_image)
            # Redirect to the profile page to display the updated data
            return redirect(url_for('profile'))
        # If user data is available, populate the form fields with existing data
        if user_data:
            return render_template('profile.html', user_data=user_data)
        else:
            # If user data is not available, render an empty form
            return render_template('profile.html')
    else:
        return redirect(url_for('login'))

def update_user_details(user_id, name, mobile_no, college, dob, address, profile_image):
    user_details = {
        'name': name,
        'mobile_no': mobile_no,
        'college': college,
        'dob': dob,
        'address': address
    }

    if profile_image:
        # Save the profile image to Firebase Storage
        storage = firebase.storage()
        image_path = f"profile_images/{user_id}_{profile_image.filename}"
        storage.child(image_path).put(profile_image)

        image_url = storage.child(image_path).get_url(None)

        # Add the profile image URL to user details
        user_details['profile_image_url'] = image_url



    db.child('users').child(user_id).update(user_details)

def add_user_to_database(user_id, email, name, mobile_no, college, dob, address,image_url=None):
    user_data = {
        'email': email,
        'name': name,
        'mobile_no': mobile_no,
        'college': college,
        'dob': dob,
        'address': address,
    }
    if image_url:
        user_data['profile_image_url'] = image_url

    db.child('users').child(user_id).set(user_data)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user'] = user['idToken']
            return redirect(url_for('profile'))
        except:
            error = "Invalid credentials. Please try again."
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin_name = request.form['admin_name']
        admin_password = request.form['admin_password']
        if admin_name == ADMIN_USERNAME and admin_password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_home'))
        else:
            error = "Invalid admin credentials."
            return render_template('admin_login.html', error=error)
    return render_template('admin_login.html')

@app.route('/admin/event', methods=['GET', 'POST'])
def admin_event():
    if 'admin' in session and session['admin']:
        if request.method == 'POST':
            # Logic to save event details in Firebase database
            event_name = request.form['event_name']
            event_by = request.form['event_by']
            event_description = request.form['event_description']
            event_type = request.form['event_type']

            start_date = request.form['start_date']
            start_time = request.form['start_time']
            end_date = request.form['end_date']
            end_time = request.form['end_time']

            # Combine date and time fields
            start_datetime = f"{start_date} {start_time}"
            end_datetime = f"{end_date} {end_time}"

            # Upload images to Firebase Storage (assuming you have configured it)
            event_image = request.files['event_image']
            event_banner = request.files['event_banner']
            storage = firebase.storage()
            image_url = None
            banner_url = None

            if event_image:
                image_path = f"images/{event_image.filename}"
                storage.child(image_path).put(event_image)
                image_url = storage.child(image_path).get_url(None)

            if event_banner:
                banner_path = f"images/{event_banner.filename}"
                storage.child(banner_path).put(event_banner)
                banner_url = storage.child(banner_path).get_url(None)

            # Save event details in Firebase database
            event_data = {
                'name': event_name,
                'by': event_by,
                'description': event_description,
                'image_url': image_url,
                'banner_url': banner_url,
                'type': event_type,
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
            }
            if event_type == 'quiz':
                quiz_duration = request.form['quiz_duration']
                num_questions = int(request.form['num_questions'])

                quiz_questions = []
                for i in range(1, num_questions + 1):
                    question_key = f"question_{i}"
                    question_text = request.form[question_key]

                    options = []
                    for j in range(1, 5):
                        option_key = f"{question_key}_option_{j}"
                        option_text = request.form[option_key]
                        options.append(option_text)

                    correct_answer_key = f"{question_key}_correct_answer"
                    correct_answer = int(request.form[correct_answer_key])

                    quiz_question = {
                        'text': question_text,
                        'options': options,
                        'correct_answer': correct_answer
                    }

                    quiz_questions.append(quiz_question)

                    # Add quiz details to event data
                event_data['quiz_duration'] = quiz_duration
                event_data['quiz_questions'] = quiz_questions
            db.child('events').push(event_data)


            return "Event created successfully!"
        return render_template('create_event.html')
    else:
        return redirect(url_for('admin_login'))

########################################

####### view_event ########

######################################

@app.route('/<event_name>', methods=['GET', 'POST'])
def view_event(event_name):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_info = auth.get_account_info(session['user'])
    user_id = user_info['users'][0]['localId']
    user_data = get_current_user_data()

    event_data = db.child('events').order_by_child('name').equal_to(event_name).get().val()
    storage = firebase.storage()



    if not event_data:
        return "Event not found", 404

    event_list = list(event_data.values())
    event = event_list[0]

    if event_list:
        event = event_list[0]
        event_id = list(event_data.keys())[0]
        event['event_id'] = event_id

    play_button = None
    if event.get('type') == 'quiz':
        play_button = True

    if request.method == 'POST' and event.get('type') == 'task':
        comment = request.form.get('comment')
        file = request.files.get('file')

        if file:
            filename = secure_filename(file.filename)
            # Upload file to Firebase Storage
            storage_path = f"submissions/{event_id}/{user_id}/{filename}"
            storage.child(storage_path).put(file)

            # Get the download URL
            file_url = storage.child(storage_path).get_url(None)

            # Save the submission details in the database
            submission_data = {
                'user_id': user_id,
                'comment': comment,
                'file_url': file_url,
                'event_id': event_id
            }
            db.child('submissions').push(submission_data)

        return redirect(url_for('view_event', event_name=event_name))

    return render_template('view_event.html', event=event, user_data=user_data, play_button=play_button)


## quiz related functions

#######################################################


@app.route('/quiz/<event_id>')
def start_quiz(event_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    # Check if user has already attempted the quiz
    user_id = auth.get_account_info(session['user'])['users'][0]['localId']
    attempt_data = db.child('quiz_results').child(user_id).child(event_id).get().val()
    if attempt_data:
        return redirect(url_for('already_attempted'))

    # First, try to retrieve the event from the general events path
    event_data = db.child('events').child(event_id).get().val()


    if not event_data or event_data.get('type') != 'quiz':
        return "Quiz not found", 404

    # Check if current time is within the event's start and end times
    current_time = datetime.now()
    start_time = datetime.strptime(event_data['start_datetime'], "%Y-%m-%d %H:%M")
    end_time = datetime.strptime(event_data['end_datetime'], "%Y-%m-%d %H:%M")

    if current_time < start_time or current_time > end_time:
        return "This quiz is not currently available", 403

    session['quiz'] = {
        'event_id': event_id,
        'current_question_index': 0,
        'score': 0,
        'start_time': time.time(),
        'quiz_duration': float(event_data['quiz_duration']) * 60,  # Convert minutes to seconds
    }

    return redirect(url_for('quiz_question', question_index=0))

############################################

## quiz question related function

############################################


@app.route('/quiz/question/<int:question_index>', methods=['GET', 'POST'])
def quiz_question(question_index):
    if 'user' not in session or 'quiz' not in session:
        return redirect(url_for('login'))

    quiz = session['quiz']
    event_id = quiz['event_id']
    current_question_index = quiz['current_question_index']
    score = quiz['score']
    start_time = quiz['start_time']
    elapsed_time = time.time() - start_time
    quiz_duration = float(quiz['quiz_duration'])

    # Check if time is up
    if elapsed_time >= quiz_duration:
        return redirect(url_for('quiz_results'))

    # Try to get event data from both 'events' and 'user_events'
    event_data = db.child('events').child(event_id).get().val()


    if not event_data:
        return "Event not found", 404

    quiz_questions = event_data['quiz_questions']

    if question_index < 0 or question_index >= len(quiz_questions):
        return "Invalid question index", 404

    current_question = quiz_questions[question_index]

    if request.method == 'POST':
        selected_answer = request.form.get('answer')
        if selected_answer is not None:
            selected_answer = int(selected_answer)
            correct_answer = current_question['correct_answer'] - 1  # Ensure correct answer index is 0-based
            if selected_answer == correct_answer:
                score += 1

        current_question_index += 1
        quiz['current_question_index'] = current_question_index
        quiz['score'] = score
        session['quiz'] = quiz

        if current_question_index < len(quiz_questions):
            return redirect(url_for('quiz_question', question_index=current_question_index))

        return redirect(url_for('quiz_results'))

    remaining_time = int(quiz_duration - elapsed_time)  # Remaining time in seconds

    return render_template(
        'quiz_question.html',
        question=current_question,
        question_index=question_index,
        quiz=quiz,
        remaining_time=remaining_time,  # Pass remaining time to template
    )

#########################################

##### quiz result related functions

#########################################

@app.route('/quiz/results')
def quiz_results():
    if 'user' not in session or 'quiz' not in session:
        return redirect(url_for('login'))

    quiz = session['quiz']
    final_score = quiz['score']
    start_time = quiz['start_time']
    end_time = time.time()
    time_taken = end_time - start_time  # Time taken in seconds

    user_info = auth.get_account_info(session['user'])
    user_id = user_info['users'][0]['localId']

    user_data = db.child('users').child(user_id).get().val()
    user_name = user_data.get('name', 'Anonymous')

    event_data = db.child('events').child(quiz['event_id']).get().val()


    if not event_data:
        return "Quiz event not found", 404

    db.child('quiz_results').child(user_id).child(quiz['event_id']).set({
        'name': user_name,
        'score': final_score,
        'time_taken': time_taken,
        'timestamp': time.time()
    })



    return render_template('quiz_results.html', final_score=final_score, time_taken=time_taken, quiz=quiz,
                           user_name=user_name)

##############################################

##### end of quiz related functions

###############################################


@app.route('/quiz/already_attempted')
def already_attempted():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('already_attempted.html')




def get_current_user_data():
    if 'user' in session:
        user_info = auth.get_account_info(session['user'])
        user_id = user_info['users'][0]['localId']
        user_data = db.child('users').child(user_id).get().val()
        return user_data
    return None

##############################################
########## contact ###########################
##############################################

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    user_data = get_current_user_data()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        contact_data = {
            'name': name,
            'email': email,
            'message': message,
            'timestamp': time.time()  # Optionally add a timestamp
        }

        # Save the contact data to Firebase (or your database)
        db.child('contacts').push(contact_data)

        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html', user_data=user_data)

####################################################

@app.route('/admin/create_blog', methods=['GET'])
def admin_create_blog():
    return render_template('create_blog.html')

@app.route('/admin/submit_blog', methods=['POST'])
def admin_submit_blog():
    if 'admin' in session:  # Ensure user is logged in
        if request.method == 'POST':
            title = request.form.get('title')
            author = request.form.get('author')
            content = request.form.get('content')

            # Get current timestamp for blog creation time
            first_image = extract_first_image(content)
            timestamp = time.time()

            # Save blog data to Firebase database
            blog_data = {
                'title': title,
                'author': author,
                'content': content,
                'banner_image': first_image,
                'timestamp': timestamp
            }
            db.child('blogs').push(blog_data)

            return redirect(url_for('admin_home'))  # Redirect to home page after successful submission

    return "Unauthorized", 401

def extract_first_image(html_content):
    # Use regular expression to find the first image tag in the HTML content
    img_tag = re.search(r'<img.*?src="(.*?)".*?>', html_content)
    if img_tag:
        return img_tag.group(1)  # Return the src attribute of the first image
    else:
        return None

@app.route('/blog/<post_id>')
def view_blog_post(post_id):
    # Fetch the specific blog post from Firebase database
    post_data = db.child('blogs').child(post_id).get().val()

    # Check if the blog post exists
    if post_data:
        return render_template('view_blog_post.html', post=post_data)
    else:
        return "Blog post not found", 404




@app.route('/generate_certificate')
def generate_certificate():
    if 'user' not in session or 'quiz' not in session:
        return redirect(url_for('login'))

    user_info = auth.get_account_info(session['user'])
    user_id = user_info['users'][0]['localId']
    user_data = db.child('users').child(user_id).get().val()
    user_name = user_data.get('name', 'Anonymous')

    event_id = session['quiz'].get('event_id')

    # Try to fetch event data from 'events' first, then 'user_events'
    event_data = db.child('events').child(event_id).get().val()


    if not event_data:
        return "Event not found", 404

    quiz_name = event_data.get('name', 'Quiz Event')
    organizer_name = event_data.get('by', 'Unknown Organizer')

    # Load the certificate template
    template_path = "static/parcer.png"
    certificate = Image.open(template_path)

    # Set up the drawing context
    draw = ImageDraw.Draw(certificate)

    # Use the default font provided by PIL
    font_name = ImageFont.truetype("static/ARIAL.TTF", size=60)
    font_quiz = ImageFont.truetype("static/ARIAL.TTF", size=60)  # Font size for the quiz name
    font_organizer = ImageFont.truetype("static/ARIAL.TTF", size=60)

    # Define text position and color
    text_color = (0, 0, 0)  # Black color

    # Adjust this position according to your template
    name_position = (700, 550)
    quiz_position = (750, 800)
    organizer_position = (780, 920)

    # Add participant's name to the certificate
    draw.text(name_position, user_name, fill=text_color, font=font_name)
    draw.text(quiz_position, quiz_name, fill=text_color, font=font_quiz)
    draw.text(organizer_position, organizer_name, fill=text_color, font=font_organizer)

    # Save the certificate to a BytesIO object
    certificate_io = io.BytesIO()
    certificate.save(certificate_io, 'PNG')
    certificate_io.seek(0)



    # Send the certificate as a downloadable file
    return send_file(certificate_io, mimetype='image/png', as_attachment=True, download_name=f'{user_name}_certificate.png')

##############################

######### admin  Leaderboard########


##############################

@app.route('/admin/leaderboard/<event_id>')
def admin_leaderboard(event_id):
    try:
        # Fetch all quiz results from the database
        all_results = db.child('quiz_results').get().val()
        event_data = db.child('events').child(event_id).get().val()

        event_name = event_data.get('name', 'Unknown Event')

        # Initialize leaderboard
        leaderboard = []

        # Process results to find scores and times for the specific event_id
        if all_results:
            for user_id, user_results in all_results.items():
                if event_id in user_results:
                    result = user_results[event_id]
                    leaderboard.append({
                        'name': result.get('name', 'Unknown'),
                        'score': result.get('score', 0),
                        'time_taken': result.get('time_taken', float('inf'))
                    })

        # Sort the leaderboard by score (high to low) and then by time_taken (low to high)
        leaderboard.sort(key=lambda x: (-x['score'], x['time_taken']))

        return render_template('admin_leaderboard.html', leaderboard=leaderboard, event_name=event_name, event_id=event_id)
    except Exception as e:
        print(f"Error fetching leaderboard data: {e}")
        return "An error occurred while fetching the leaderboard.", 500


##################
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.template_filter('enumerate')
def enumerate_filter(iterable):
    return enumerate(iterable)

##############################



#############################

@app.route('/submissions/<event_id>')
def view_submissions(event_id):
    # Retrieve submissions
    submissions = db.child('submissions').order_by_child('event_id').equal_to(event_id).get().val()
    print("submissions : ", submissions)

    event_data = db.child('events').child(event_id).get().val()
    event_name = event_data.get('name')

    if not submissions:
        return "No submissions found", 404

    # Retrieve event data

    # Retrieve user details
    user_ids = {submission['user_id'] for submission in submissions.values() if 'user_id' in submission}
    user_details = {}
    for user_id in user_ids:
        user_info = db.child('users').child(user_id).get().val()  # Assuming user details are stored under 'users'
        if user_info:
            user_details[user_id] = user_info

    # Attach user details to submissions
    for submission_id, submission in submissions.items():
        user_id = submission.get('user_id')
        if user_id and user_id in user_details:
            submission['user_info'] = user_details[user_id]

    return render_template('submissions.html', submissions=submissions, event_name=event_name)
####################################




################################


##############################

@app.route('/admin/export_leaderboard/<event_id>', methods=['GET'])
def export_leaderboard(event_id):
    try:
        all_results = db.child('quiz_results').get().val()
        event_data = db.child('events').child(event_id).get().val()
        leaderboard = []

        if all_results:
            for user_id, user_results in all_results.items():
                if event_id in user_results:
                    result = user_results[event_id]
                    leaderboard.append({
                        'name': result.get('name', 'Unknown'),
                        'score': result.get('score', 0),
                        'time_taken': result.get('time_taken', float('inf'))
                    })

        leaderboard.sort(key=lambda x: (-x['score'], x['time_taken']))

        # Convert leaderboard to DataFrame
        df = pd.DataFrame(leaderboard)

        # Create an in-memory file and save the DataFrame to it as a CSV
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)

        # Send the file as a downloadable response
        return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name=f'leaderboard_{event_id}.csv')

    except Exception as e:
        print(f"Error exporting leaderboard data: {e}")
        return "An error occurred while exporting the leaderboard.", 500
#####################################


@app.route('/user/event', methods=['GET', 'POST'])
def user_event():
    if 'user' in session:
        user_info = auth.get_account_info(session['user'])
        user_id = user_info['users'][0]['localId']
        user_data = db.child('users').child(user_id).get().val()
        user_name = user_data.get('name', 'Anonymous')

        # Assuming you store user ID in the session
        if request.method == 'POST':
            # Logic to save event details in Firebase database
            event_name = request.form['event_name']
            event_by = user_name  # Assuming username is stored in session
            event_description = request.form['event_description']
            event_type = request.form['event_type']

            start_date = request.form['start_date']
            start_time = request.form['start_time']
            end_date = request.form['end_date']
            end_time = request.form['end_time']

            # Combine date and time fields
            start_datetime = f"{start_date} {start_time}"
            end_datetime = f"{end_date} {end_time}"

            # Upload images to Firebase Storage (if any)
            event_image = request.files['event_image']
            event_banner = request.files['event_banner']
            storage = firebase.storage()
            image_url = None
            banner_url = None

            if event_image:
                image_path = f"images/{event_image.filename}"
                storage.child(image_path).put(event_image)
                image_url = storage.child(image_path).get_url(None)

            if event_banner:
                banner_path = f"images/{event_banner.filename}"
                storage.child(banner_path).put(event_banner)
                banner_url = storage.child(banner_path).get_url(None)

            # Save event details in Firebase database under user_id
            event_data = {
                'name': event_name,
                'by': event_by,
                'description': event_description,
                'image_url': image_url,
                'banner_url': banner_url,
                'type': event_type,
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
            }

            if event_type == 'quiz':
                quiz_duration = request.form['quiz_duration']
                num_questions = int(request.form['num_questions'])

                quiz_questions = []
                for i in range(1, num_questions + 1):
                    question_key = f"question_{i}"
                    question_text = request.form[question_key]

                    options = []
                    for j in range(1, 5):
                        option_key = f"{question_key}_option_{j}"
                        option_text = request.form[option_key]
                        options.append(option_text)

                    correct_answer_key = f"{question_key}_correct_answer"
                    correct_answer = int(request.form[correct_answer_key])

                    quiz_question = {
                        'text': question_text,
                        'options': options,
                        'correct_answer': correct_answer
                    }

                    quiz_questions.append(quiz_question)

                event_data['quiz_duration'] = quiz_duration
                event_data['quiz_questions'] = quiz_questions

            db.child('events').push(event_data)

            return "Event created successfully!"
        return render_template('create_event.html')
    else:
        return redirect(url_for('login'))

@app.template_filter('to_datetime')
def to_datetime(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


if __name__ == '__main__':
    app.run(debug=True)
