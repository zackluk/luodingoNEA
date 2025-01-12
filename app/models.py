from . import db, migrate
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), nullable=False, unique=True)
    username = db.Column(db.String(64), nullable=False, unique=True)
    password = db.Column(db.String(64), nullable=False)
    progress = db.Column(db.Integer, nullable=False)

    # Define relationship with UserQuestion, avoiding duplicate backrefs
    user_questions = db.relationship('UserQuestion', back_populates='user', lazy=True)

    user_lessons = db.relationship('UserLesson', back_populates='user', lazy=True)

    def __repr__(self):
        return f'{self.id} {self.email} {self.username} {self.password} {self.progress}'

class Lesson(db.Model):
    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key=True)
    deck = db.Column(JSON, nullable=False)
    notes = db.Column(db.String(256), nullable=True)
    lessonType = db.Column(db.String(32))

    user_lessons = db.relationship('UserLesson', back_populates='lesson', lazy=True)

    def __repr__(self):
        return f'{self.id} {self.deck} {self.notes} {self.lessonType}'

class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(256), nullable=False)
    answer = db.Column(db.String(256), nullable=False)
    questionType = db.Column(db.String(32), nullable=False)
    options = db.Column(JSON, nullable=True)

    # Define relationship with UserQuestion
    question_questions = db.relationship('UserQuestion', back_populates='question', lazy=True)

    def __repr__(self):
        return f'{self.id} {self.question} {self.answer} {self.questionType} {self.options}'

class UserQuestion(db.Model):
    __tablename__ = 'user_questions'

    userId = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, primary_key=True)
    questionId = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, primary_key=True)

    # Supermemo fields
    interval = db.Column(db.Integer, default=0)
    easiness = db.Column(db.Float, default=2.5)  # Changed to Float for decimal value
    date = db.Column(db.DateTime, default=datetime.now)
    repetitions = db.Column(db.Integer, default=0)

    # Relationships
    user = db.relationship('User', back_populates='user_questions', overlaps='user_questions_assoc')
    question = db.relationship('Question', back_populates='question_questions', overlaps='user_questions_questions')

    def __repr__(self):
        return f'{self.userId} {self.questionId} {self.interval} {self.easiness} {self.date} {self.repetitions}'

class UserLesson(db.Model):
    __tablename__ = 'user_lessons'

    userId = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, primary_key=True)
    lessonId = db.Column(db.Integer, db.ForeignKey('lessons.id', ondelete='CASCADE'), nullable=False, primary_key=True)

    state = db.Column(db.String, default = 'Incomplete')

    user = db.relationship('User', back_populates='user_lessons')
    lesson = db.relationship('Lesson', back_populates='user_lessons')

    def __repr__(self):
        return f'{self.userId} {self.lessonId} {self.state}'
    
class DailyWord(db.Model):
    __tablename__ = 'daily_words'

    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(64), nullable=False)
    translation = db.Column(db.String(64), nullable=False)
    sentence = db.Column(db.String(512), nullable=False)
    fact = db.Column(db.String(512), nullable=True)
    date = db.Column(db.Date, default=datetime.today().date())

    def __repr__(self):
        return f'{self.id} {self.word} {self.translation} {self.sentence} {self.fact} {self.date}'