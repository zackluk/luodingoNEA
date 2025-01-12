import json
import random
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify, send_file, after_this_request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from flask_mail import Message
from .models import User, Lesson, Question, UserQuestion, UserLesson
from .utils import *
from . import db, mail
from sqlalchemy import update, insert, delete
from datetime import datetime
#using werkzeug because it offers more flexibility and does not limit algorithm to just bcrypt -> it is also usually faster
#using hashlib would create too much unnecessary work

routes = Blueprint('routes', __name__)
#just telling python that this file is a blueprint for storing all the routes

random.seed()

@routes.route('/', methods = ['GET', 'POST'])
@routes.route('/login', methods = ['GET', 'POST'])
def login():
   if request.method == 'POST':
       username = request.form.get('username')
       password = request.form.get('password')

       user = User.query.filter_by(username = username).first()

       if not user:
           #aka user does not exist
           flash('Incorrect username or username does not exist', category = 'error')
           return render_template('login.html')

       else:
            if check_password_hash(user.password, password):
            #comparing the password stored in the user instance/object to the one entered in the form
               flash('Successful Login', category = 'success')
               login_user(user, remember = True)

               return redirect(url_for('routes.learn'))
               #redirecting the user to the home page if they are sucessful at logging in

            else:
               flash('Incorect password', category = 'error')
               return render_template('login.html')

   return render_template('login.html')


@routes.route('/sign-up', methods = ['GET', 'POST'])
@routes.route('/create-an-account', methods = ['GET', 'POST'])
def signUp():
   if request.method == 'POST':
       email = request.form.get('email')
       username = request.form.get('username')
       password = request.form.get('password')
       confirmPassword = request.form.get('confirmPassword')

       errors = []

       if not validateEmail(email):
           errors.append('Invalid Email')

       if notUniqueUsername(username):
           errors.append('Username already taken')

       if password != confirmPassword:
           errors.append('Passwords do not match')

       if not validatePassword(password):
           errors.append('Invalid Password')

       if errors:
           for error in errors:
               flash(error, category = 'error')
           return render_template('signUp.html')

       else:
           newUser = User(email = email, username = username, password = generate_password_hash(password), progress = 0)

           db.session.add(newUser)
           #adding new user entry
           db.session.commit()

           flash('Account created, login to start learning!', category = 'success')
           #provides a confirmation message when account is created successfully

           return redirect(url_for('routes.login'))
           #get user to login with their just-created login credentials

   return render_template('signUp.html')


@routes.route('/logout')
@login_required
#make sure that you must be logged in to log out
def logout():
   logout_user()
   return redirect(url_for('routes.login'))

@routes.route('/forgor-password', methods = ['GET', 'POST'])
def forgorPassword():
   if request.method == 'POST':
       email = request.form.get('email')
       user = User.query.filter_by(email = email).first()
       #checking if the email exists in the database

       if user:
           flash(f'A link to reset your password has been sent to {email}', category = 'success')

           resetToken = generateResetToken(user.email)
           #creating token, which would be saved within the reset link

           msg = Message(subject = 'Luodingo Password Reset', recipients = [email], body = f'Reset password with this link: {url_for(f"routes.resetPassword", token = resetToken, _external = True)}\n\nThis link expires in 1 hour.')
           #_external = True to show the absolute URL, rather than the relative one

           mail.send(msg)
           return redirect(url_for('routes.login'))


       else:
           flash(f'{email} is not in the database, sign up to create an account or try again', category = 'error')
           return render_template('forgorPassword.html')

   return render_template('forgorPassword.html')


@routes.route('/reset-password/<token>', methods = ['GET', 'POST'])
def resetPassword(token):
   email = verifyResetToken(token)

   if not email:
       flash('The reset link is invalid or has expired', category = 'error')
       return redirect(url_for('routes.login')) 

   if request.method == 'POST':
       password = request.form.get('password')
       confirmPassword = request.form.get('confirmPassword')

       errors = []

       if password != confirmPassword:
           errors.append('Passwords do not match')

       if not validatePassword(password):
           errors.append('Invalid Password')

       if errors:
           for error in errors:
               flash(error, category = 'error')
           return render_template('resetPassword.html', token = token)

       else:
           user = User.query.filter_by(email = email).first()

           user.password = generate_password_hash(password)
           db.session.commit()
           flash('Password has been updated', category = 'success')

           return redirect(url_for('routes.login'))

   return render_template('resetPassword.html', token = token)

@routes.route('/reset-username', methods = ['GET', 'POST'])
def resetUsername():
    if request.method == 'POST':
        newUsername = request.form.get('username')

        user = User.query.filter_by(id = current_user.id).first()

        if not notUniqueUsername(newUsername):
            #so username is unique
            user.username = newUsername
            db.session.commit()
            flash('Username has been updated', category = 'success')

        else:
            flash('Username already taken', category = 'error')
            return render_template('resetUsername.html')

    return render_template('resetUsername.html')

@routes.route('/reset-progress', methods = ['GET', 'POST'])
def resetProgress():
    if current_user.email == 'lukz@merciaschool.com':
        if request.method == 'POST':
            userId = request.form.get('userId')

            user = User.query.filter_by(id = userId).first()

            user.progress = 0
            db.session.commit()
            flash('User progress has been reset.', category = 'success')

        return render_template('resetProgress.html')

    else:
        flash('Access restricted... You will be redirected to the learn page.', category='error')
        return redirect(url_for('routes.learn'))

@routes.route('/home', methods = ['GET', 'POST'])
@routes.route('/learn', methods = ['GET', 'POST'])
@login_required
def learn():
    if request.method == 'POST':
        lessonId = int(request.form.get('lesson'))

        return redirect(url_for('routes.lesson', lessonId = lessonId))
    
    userCompletedLessons = UserLesson.query.with_entities(UserLesson.lessonId).filter_by(userId=current_user.id, state='Completed').all()
    #will find all completed lessons of the user (returns a list of tuples)
    userCompletedLessons = [lessonId for (lessonId, ) in userCompletedLessons]

    higherUserRank = User.query.filter(User.progress > current_user.progress).count()
    userRank = higherUserRank + 1

    dailyWord = generateWordOfTheDay()

    existingWords = [entry.word for entry in DailyWord.query.all()]

    if dailyWord not in existingWords:
        db.session.add(dailyWord)
        db.session.commit()

    rightBarData = (userRank, current_user.progress, dailyWord)

    learnLessons = Lesson.query.with_entities(Lesson.id).filter_by(lessonType = 'learn').all()
    learnLessons = [lessonId for (lessonId,) in learnLessons]

    return render_template('learn.html', userCompletedLessons = userCompletedLessons, rightBarData = rightBarData, learnLessons = learnLessons)

@routes.route('/grammar', methods = ['GET', 'POST'])
@login_required
def grammar():
    if request.method == 'POST':
        lessonId = int(request.form.get('lesson'))
        return redirect(url_for('routes.lesson', lessonId = lessonId))
    
    userCompletedLessons = UserLesson.query.with_entities(UserLesson.lessonId).filter_by(userId=current_user.id, state='Completed').all()
    userCompletedLessons = [lessonId for (lessonId, ) in userCompletedLessons]

    higherUserRank = User.query.filter(User.progress > current_user.progress).count()
    userRank = higherUserRank + 1

    dailyWord = generateWordOfTheDay()

    existingWords = [entry.word for entry in DailyWord.query.all()]

    if dailyWord not in existingWords:
        db.session.add(dailyWord)
        db.session.commit()

    rightBarData = (userRank, current_user.progress, dailyWord)

    grammarLessons = Lesson.query.with_entities(Lesson.id).filter_by(lessonType = 'grammar').all()
    grammarLessons = [lessonId for (lessonId,) in grammarLessons]

    return render_template('grammar.html', userCompletedLessons = userCompletedLessons, rightBarData = rightBarData, grammarLessons = grammarLessons)

@routes.route('/retrieval', methods = ['GET', 'POST'])
@login_required
def retrieval():
    if request.method == 'POST':
        #kind of forced to use Lesson model, since the questions always redirect back to the lesson.
        #maybe a good idea to make temporary lesson instances, since the interval for each question could change a lot
        currentTime = datetime.now()

        retrieveQuestions = UserQuestion.query.filter(UserQuestion.date <= currentTime).order_by(UserQuestion.date.asc()).limit(12).all()
        #parameter in filter function makes it return entries that have dates equal to or past the current time
        #this should return the questions by their dates in ascending order
        #limit method here states that the max number of questions for this deck is 12, since I think if it was longer it might feel endless for the user

        if retrieveQuestions:
            #i.e. there is something to retrieve
            tempLessonDeck = [int(question.questionId) for question in retrieveQuestions]

            retrievalLesson = Lesson(deck = tempLessonDeck, notes = None, lessonType = 'retrieval')
            db.session.add(retrievalLesson)
            db.session.commit()

            return redirect(url_for('routes.lesson', lessonId = retrievalLesson.id))
        
        else:
            flash('Congratulations, you do not have any questions to retieve! You will now be redirected to the learn page')
            return redirect(url_for('routes.learn'))
        
    higherUserRank = User.query.filter(User.progress > current_user.progress).count()
    userRank = higherUserRank + 1

    dailyWord = generateWordOfTheDay()

    existingWords = [entry.word for entry in DailyWord.query.all()]

    if dailyWord not in existingWords:
        db.session.add(dailyWord)
        db.session.commit()

    rightBarData = (userRank, current_user.progress, dailyWord)

    return render_template('retrieval.html', rightBarData = rightBarData)

@routes.route('/leaderboard')
@login_required
def leaderboard():
    topFiveUsers = User.query.order_by(User.progress.desc()).limit(5).all()
    #will return at most 5 instances of User

    rankings = [(User.query.filter(User.progress > user.progress).count(), user.username, user.progress) for user in topFiveUsers]
    #returns their true rank.

    higherUserRank = User.query.filter(User.progress > current_user.progress).count()
    userRank = higherUserRank + 1

    dailyWord = generateWordOfTheDay()

    existingWords = [entry.word for entry in DailyWord.query.all()]

    if dailyWord not in existingWords:
        db.session.add(dailyWord)
        db.session.commit()

    rightBarData = (userRank, current_user.progress, dailyWord)

    return render_template('leaderboard.html', rankings = rankings, userRank = (userRank, current_user.username, current_user.progress), rightBarData = rightBarData)

@routes.route('/profile', methods = ['GET', 'POST'])
@login_required
def profile():
    user = User.query.filter_by(id = current_user.id).first()

    higherUserRank = User.query.filter(User.progress > current_user.progress).count()
    userRank = higherUserRank + 1

    dailyWord = generateWordOfTheDay()

    existingWords = [entry.word for entry in DailyWord.query.all()]

    if dailyWord not in existingWords:
        db.session.add(dailyWord)
        db.session.commit()

    rightBarData = (userRank, current_user.progress, dailyWord)

    if request.method == 'POST':
        userRequest = request.form.get('action')

        if userRequest == 'change-username':
            return redirect(url_for('routes.resetUsername'))
        
        else:
            return redirect(url_for('routes.resetPassword'))

    return render_template('profile.html', user = user, rightBarData = rightBarData)

@routes.route('/add-lesson', methods = ['GET', 'POST'])
@login_required
def addLesson():
    if current_user.email == 'lukz@merciaschool.com':
        questions = Question.query.all()
        lessons = Lesson.query.all()

        if request.method == 'POST':
            lessonJson = request.form.get('lesson')
            lessonType = request.form.get('lessonType')
            notes = request.form.get('notes')
            #currenty a string

            lessonPyList = json.loads(lessonJson)
            newLesson = Lesson(deck = lessonPyList, notes = notes, lessonType = lessonType)

            db.session.add(newLesson)
            db.session.commit()
            flash('Lesson has been added.', category = 'success')

            lessons = Lesson.query.all()

        return render_template('addLesson.html', lessons = lessons, questions = questions)

    else:
        flash('Access restricted... You will be redirected to the learn page.', category = 'error')
        #need to fix this flash message not showing -> shows up only when the user logs out
        return redirect(url_for('routes.learn'))
    
@routes.route('/delete-lesson/<int:lessonId>', methods = ['POST'])
@login_required
def deleteLesson(lessonId):
    if current_user.email == 'lukz@merciaschool.com':
        lesson = Lesson.query.filter_by(id = lessonId).first()
        db.session.delete(lesson)
        db.session.commit()
        flash('Lesson has been deleted', category = 'success')

        return redirect(url_for('routes.addLesson'))
    
    else:
        flash('Access restricted... Yo uwill be redicreted to the learn page.', category = 'error')
        return redirect(url_for('routes.learn'))

@routes.route('/add-question', methods=['GET', 'POST'])
@login_required
def addQuestion():
    if current_user.email == 'lukz@merciaschool.com':
        questions = Question.query.all() 
        # Fetch all questions from the database

        if request.method == 'POST':
            question = request.form.get('question')
            answer = request.form.get('answer')
            questionType = request.form.get('questionType')

            if questionType == 'multiple-choice' or questionType == 'fill-in-the-blank':
                options = set()
                options.add(answer)

                while len(options) < 3:
                    newOptions = generateOptions(question)
                    print(newOptions)
                    if newOptions:
                        options.add(newOptions[0])
                        options.add(newOptions[1])

                options = list(options)
                optionsJson = json.dumps(options)
                #moved from question route to here, so there is less mystery as to what options are being generated
            else:
                optionsJson = None

            newQuestion = Question(question = question, answer = answer, questionType = questionType, options = optionsJson)
            db.session.add(newQuestion)
            db.session.commit()
            flash('Question has been added.', category='success')
            
            # Refetch questions after adding a new one to show the updated list
            questions = Question.query.all()

        return render_template('addQuestion.html', questions=questions)
    
    else:
        flash('Access restricted... You will be redirected to the learn page.', category='error')
        return redirect(url_for('routes.learn'))

@routes.route('/delete-question/<int:questionId>', methods = ['POST'])
@login_required
def deleteQuestion(questionId):
    if current_user.email == 'lukz@merciaschool.com':
        question = Question.query.filter_by(id = questionId).first()

        db.session.delete(question)
        db.session.commit()
        flash('Question has been deleted', category = 'success')

        return redirect(url_for('routes.addQuestion'))
    
    else:
        flash('Access restricted... You will be redirected to the learn page.', category='error')
        return redirect(url_for('routes.learn'))
    
@routes.route('/user-questions', methods = ['GET', 'POST'])
@login_required
def userQuestions():
    if current_user.email == 'lukz@merciaschool.com':
        userQuestions = UserQuestion.query.all()

        return render_template('userQuestions.html', userQuestions = userQuestions)

    else:
        flash('Access restricted... You will be redirected to the learn page.', category='error')
        return redirect(url_for('routes.learn'))
    
@routes.route('/delete-user-question/<int:userId>/<int:questionId>', methods = ['POST'])
@login_required
def deleteUserQuestion(userId, questionId):
    if current_user.email == 'lukz@merciaschool.com':
        userQuestion = UserQuestion.query.filter_by(userId = userId, questionId = questionId).first()

        db.session.delete(userQuestion)
        db.session.commit()
        flash('UserQuestion has been deleted', category = 'success')

        return redirect(url_for('routes.userQuestions'))
    
    else:
        flash('Access restricted... You will be redirected to the learn page.', category='error')
        return redirect(url_for('routes.learn'))

@routes.route('/user-lessons', methods = ['GET', 'POST'])
@login_required
def userLessons():
    if current_user.email == 'lukz@merciaschool.com':
        userLessons = UserLesson.query.all()

        return render_template('userLessons.html', userLessons = userLessons)

    else:
        flash('Access restricted... You will be redirected to the learn page.', category='error')
        return redirect(url_for('routes.learn'))

@routes.route('/delete-user-lesson/<int:userId>/<int:lessonId>', methods = ['POST'])
@login_required
def deleteUserLesson(userId, lessonId):
    if current_user.email == 'lukz@merciaschool.com':
        userLesson = UserLesson.query.filter_by(userId = userId, lessonId = lessonId).first()

        db.session.delete(userLesson)
        db.session.commit()
        flash('UserLesson has been deleted', category = 'success')

        return redirect(url_for('routes.userLessons'))
    
    else:
        flash('Access restricted... You will be redirected to the learn page.', category='error')
        return redirect(url_for('routes.learn'))
    
@routes.route('/users', methods = ['GET', 'POST'])
@login_required
def users():
    if current_user.email == 'lukz@merciaschool.com':
        users = User.query.all()

        print(users)

        return render_template('users.html', users = users)

    else:
        flash('Access restricted... You will be redirected to the learn page.', category='error')
        return redirect(url_for('routes.learn'))
    
@routes.route('/delete-user/<int:userId>', methods = ['POST'])
@login_required
def deleteUser(userId):
    if current_user.email == 'lukz@merciaschool.com':

        userQuestions = UserQuestion.query.filter_by(userId = userId).all()
        for userQuestion in userQuestions:
            db.session.delete(userQuestion)

        user = User.query.filter_by(id = userId).first()

        db.session.delete(user)
        db.session.commit()
        flash('User has been deleted', category = 'success')

        return redirect(url_for('routes.users'))
    
    else:
        flash('Access restricted... You will be redirected to the learn page.', category='error')
        return redirect(url_for('routes.learn'))
    
@routes.route('/daily-words', methods = ['GET', 'POST'])
@login_required
def dailyWords():
    if current_user.email == 'lukz@merciaschool.com':
        dailyWords = DailyWord.query.all()

        return render_template('dailyWords.html', dailyWords = dailyWords)

    else:
        flash('Access restricted... You will be redirected to the learn page.', category='error')
        return redirect(url_for('routes.learn'))
    
@routes.route('/delete-daliy-word/<int:wordId>', methods = ['POST'])
@login_required
def deleteDailyWord(wordId):
    if current_user.email == 'lukz@merciaschool.com':
        dailyWord = DailyWord.query.filter_by(id = wordId).first()

        db.session.delete(dailyWord)
        db.session.commit()
        flash('User has been deleted', category = 'success')

        return redirect(url_for('routes.dailyWords'))
    
    else:
        flash('Access restricted... You will be redirected to the learn page.', category='error')
        return redirect(url_for('routes.learn'))
    
@routes.route('/admin', methods = ['GET', 'POST'])
@login_required
def admin():
    if current_user.email == 'lukz@merciaschool.com':
        return render_template('admin.html')
    
    else:
        flash('Access restricted... You will be redirected to the learn page.', category='error')
        return redirect(url_for('routes.learn'))


@routes.route('/lesson/<int:lessonId>', methods = ['GET', 'POST'])
@login_required
def lesson(lessonId):
    lesson = Lesson.query.filter_by(id = lessonId).first()
    userLesson = UserLesson.query.filter_by(userId = current_user.id, lessonId = lessonId).first()

    if not lesson:
        flash('Lesson could not be found... You will be redirected to the learn page.', category = 'error')
        return redirect(url_for('routes.learn'))

    session['lessonDeck'] = lesson.deck
    session['progress'] = {'completedQuestions': 0, 'totalQuestions': len(lesson.deck)}
    #needed to track progress for the progress bar

    if userLesson == None:
        newUserLesson = UserLesson(userId = current_user.id, lessonId = lessonId)
        db.session.add(newUserLesson)
        db.session.commit()
        #will make the state of the lesson's state incomplete

    return redirect(url_for('routes.question', lessonId = lessonId, questionId = session['lessonDeck'][0]))
    #start with item at index 0 because it would be the start of the list

@routes.route('/lesson/<int:lessonId>/question/<int:questionId>', methods = ['GET', 'POST'])
@login_required
def question(lessonId, questionId):
    question = Question.query.filter_by(id = questionId).first()
    lesson = Lesson.query.filter_by(id = lessonId).first()
    startTime = datetime.now()
    #needed for the automated marking
    userQuestion = UserQuestion.query.filter_by(userId = current_user.id, questionId = questionId).first()

    progress = session['progress']
    progressPercentage = (progress['completedQuestions'] / progress['totalQuestions']) * 100

    if request.method == 'POST':

        userAnswer = request.form.get('answer')

        if userAnswer == '':
            flash('Answers cannot be empty!', 'error')
            return redirect(url_for('routes.question', lessonId = lessonId, questionId = questionId))
            #thought this would be easier than just rendering template with a bunch of parameters, even tho load speed might be slighlty slower

        if validateAnswer(userAnswer):
            flash('Answers should not contain special characters or symbols other than punctuation!', 'error')
            return redirect(url_for('routes.question', lessonId = lessonId, questionId = questionId))

        userAnswer = userAnswer.strip()
        #when buttons removed/ user changes mind and decides to delete their current orientation of buttons, there is always a leading space remaning, so need to compensate doing this

        endTime = datetime.now()
        session['userAnswer'] = userAnswer
        result = checkAnswer(userAnswer, question.answer)
        #moved this out of the result parameter in the redirect function, since will be needed for the automated marking

        duration = endTime - startTime

        score = automatedMarking(result, duration)
        
        if userQuestion == None:
            #so first time encountering the question
            newUserQuestion = UserQuestion(userId = current_user.id, questionId = questionId)
            db.session.add(newUserQuestion)
            db.session.commit()

            firstReview(newUserQuestion, score)

        else:
            updateReview(userQuestion, score)

        db.session.commit()
        #this alone should be enough, since the attributes should've been temporarily updated within the firstReview and updateReview subroutines

        return redirect(url_for('routes.result', lessonId = lesson.id, questionId = questionId, result = result))
        #will have to change this in real implementation!

    ttsUrl = url_for('routes.getAudio', questionId = questionId)

    if question.questionType == 'multiple-choice' or question.questionType == 'fill-in-the-blank':

        options = json.loads(question.options)

        random.shuffle(options)
        #shuffling list such that the options won't be at the same location every time

        questionLeft = ''
        questionRight = ''

        if question.questionType == 'fill-in-the-blank':
            questionList = question.question.split('_')
            questionLeft = questionList[0]
            questionRight = questionList[1]

        return render_template('question.html', lesson = lesson, question = question, questionLeft = questionLeft, questionRight = questionRight, option1 = options[0], option2 = options[1], option3 = options[2], progress = progressPercentage, audioPath = ttsUrl)

    if question.questionType == 'mouse-navigation':
        if question.options == None:
            answerList = createAnswerList(question.answer)
            options = generateExtraBlocks(question, answerList)
    
            optionsJson = json.dumps(options)
            question.options = optionsJson
            
            db.session.commit()

        options = json.loads(question.options)

        print(options)

        random.shuffle(options)
        #added this such that the orientation of the blocks will not be too obvious

        return render_template('question.html', lesson = lesson , question = question, progress = progressPercentage, audioPath = ttsUrl, answerList = options)

    #so this can only be mic-input and keyboard-input
    return render_template('question.html', lesson = lesson, question = question, progress = progressPercentage, audioPath = ttsUrl)

@routes.route('/lesson/<int:lessonId>/question/<int:questionId>/<string:result>', methods = ['GET', 'POST'])
@login_required
def result(lessonId, questionId, result):
    question = Question.query.filter_by(id = questionId).first()
    lesson = Lesson.query.filter_by(id = lessonId).first()

    currentList = session['lessonDeck']
    progress = session['progress']

    if request.method == 'POST':
        if question.questionType == 'mic-input':    
            os.remove('temp/transcription.txt')
            #removes transcript from already answered question

        if len(currentList) > 0:
            return redirect(url_for('routes.question', lessonId = lesson.id, questionId = currentList[0]))

        else:
            return redirect(url_for('routes.summary', lessonId = lessonId))
            #aka the lesson has been completed

    else:
        session['lessonDeck'] = currentList
        session['progress'] = progress
        #setting the session variables to the new updated values to ensure that the values cannot be updated 'late'

        currentList.remove(questionId)
        progress['completedQuestions'] += 1

        if result == 'correct':
            message =  'Correct! +2XP'
            #might be good to add translation of the phrase they just translated if it is fill-in-the-blanks

        else:
            message = 'Correct Solution:'
            currentList.append(questionId)

            # if question.questionType == 'keyboard-input':
            #     #short one sentence explanation of why the answer is wrong
            #     message += incorrectReason(question, session['userAnswer'])

            progress['totalQuestions'] += 1

        progressPercentage = (progress['completedQuestions'] / progress['totalQuestions']) * 100

        return render_template('questionResult.html', lesson = lesson, lessonDeck = currentList, question = question, result = result, message = message, progress = progressPercentage)

@routes.route('/audio/<int:questionId>')
@login_required
def getAudio(questionId):
    question = Question.query.filter_by(id = questionId).first()

    tempDir = os.path.join(os.getcwd(), 'app', 'temp')

    if not os.path.exists(tempDir):
        os.makedirs(tempDir)

    speakQuestion(generateSpeechText(question), question.id)
    #procedure call

    ttsPath = os.path.join(tempDir, f'tempCombined{questionId}.mp3')

    @after_this_request
    def removeFile(response):
        try:
            os.remove(ttsPath)
        except OSError as e:
            pass

        return response

    return send_file(ttsPath, mimetype = 'audio/mpeg', as_attachment = False)

@routes.route('/lesson/<int:lessonId>/summary', methods = ['GET', 'POST'])
@login_required
def summary(lessonId):
    lesson = Lesson.query.filter_by(id = lessonId).first()
    userLesson = UserLesson.query.filter_by(userId = current_user.id, lessonId = lessonId).first()

    userLesson.state = 'Completed'
    db.session.commit()
    #updating userLesson state

    if request.method == 'POST':
        if lesson.lessonType == 'retrieval':
            db.session.delete(userLesson)
            db.session.delete(lesson)
            db.session.commit()
            return redirect(url_for('routes.retrieval'))

        if lessonId < 5:
            #hard-coding this currently
            return redirect(url_for('routes.learn'))

        else:
            return redirect(url_for('routes.grammar'))
        #redirect user when they have clicked on 'endlesson' button

    progress = session['progress']
    accuracy = round(100 - ((progress['totalQuestions'] - len(lesson.deck)) / len(lesson.deck) * 100))
    #subtraction inside brackets is finding the error rate
    #* 100 to get a percentage for error rate
    #100 - error rate to get accuracy

    xp = 0

    for questionId in lesson.deck:
        userQuestion = UserQuestion.query.filter_by(userId = current_user.id, questionId = questionId).first()

        xp += decideQuestionXP(userQuestion)

    joke = generateJoke()

    user = User.query.filter_by(id = current_user.id).first()
    user.progress += xp
    db.session.commit()
    #updates the user's xp

    return render_template('summary.html', lesson = lesson, accuracy = accuracy, xp = xp, joke = joke)

@routes.route('/transcribe', methods = ['POST'])
@login_required
def transcribe():
    data = request.get_json()
    text = data.get('text', '')

    with open('temp/transcription.txt', 'w') as file:
        file.write(text)

    #transcription will need to be deleted later, probably in the results route
    return {'message': 'Transcription saved successfully'}, 200