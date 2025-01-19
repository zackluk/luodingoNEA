import re
import os
import random
from .models import User, DailyWord
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import current_app
from openai import OpenAI
from gtts import gTTS
from dotenv import load_dotenv
from os import getenv
from moviepy import AudioFileClip, concatenate_audioclips
from tempfile import NamedTemporaryFile
from supermemo2 import review, first_review
from datetime import datetime

load_dotenv()
client = OpenAI(api_key = getenv('API_KEY'))
random.seed()

def validateEmail(email):
   return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))
   #bool() to convert the output value into boolean, which makes it much easier


def validatePassword(password):
   return bool(re.match(r"""^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+[\]{};':",.<>?`~\\|/-]).{8,}$""", password))
   #had to use triple quotes because regex pattern included both '' and ""


def notUniqueUsername(createUsername):
   return User.query.filter_by(username = createUsername).first()
   #returns true which means username taken in is not unique because it already exists in the database


def generateResetToken(email):
   return URLSafeTimedSerializer(current_app.config['SECRET_KEY']).dumps(email)


def verifyResetToken(token, expiration = 3600):
   serialiser = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

   try:
       email = serialiser.loads(token, max_age = expiration)


   except (SignatureExpired, BadSignature):
       return None
   
   return email

def checkAnswer(userAnswer, correctAnswer):
   if userAnswer == correctAnswer:
      return 'correct'

   else:
      return 'incorrect'
   
def validateAnswer(userAnswer):
   return bool(re.search(r"""[^\w\s.,;!?'"(){}\[\]:\-_/\\]""", userAnswer))
   #returns true if special characters are detected

def generateOptions(question):
   try:
      stream = client.chat.completions.create(
         model="gpt-4o-mini",  # Ensure you're using the correct model name
         messages=[
            {
               "role": "system",
               "content": """
               You are an algorithm for generating alternative options to the correct answer for a multiple-choice question.
               Give two INCORRECT answers for the question that has been provided, for the user to choose from.
               Only reply with the two other options, return the value as two words separated by a comma in between.
               """
            },
            {
               "role": "user",
               "content": f"""
               The word for the multiple choice question is the German word: '{question}'
               Give me two INCORRECT answers for '{question}' for the user to choose from.
               If {question} is in the form 'to _', return only the infinitive of the verb, and do not include the German word 'zu'.
               If {question} is a verb, return the German word, alongside its article. E.g. 'Der Name' when the question is 'Name'.
               If {question} has a pronoun at the start, only give a single word answer as your response. E.g. 'Ich _ aus Deutschland', you should return words like 'komme', with the ich-conjugation.
               If {question} is a question and ends with a question mark, your responses should be questions.
               """
            }
         ]
      )
      
      response = stream.choices[0].message.content
      options = response.split(',')

      return options
   
   except Exception:
      return 'Error'
   
def incorrectReason(question, answer):
   #currently not working, maybe leave it till later
   try:
      stream = client.chat.completions.create(
      messages = [
            {
               "role": "system",
               "content": """
               You are an algorithm for correcting german translation questions.
               Give a one sentence response to tell the user why their answer was incorrect.
               """
            },
            {
               "role": "user",
               "content": f"""
               Here is the original question: '{question.question}'
               Here is my answer: '{answer}'
               Give me a one sentence answer as to why my answer is incorrect
               """
            }
         ]
      )

   except Exception:
      return 'Error'

def tts(text, lang = 'de'):
   tts = gTTS(text = text, lang = lang, tld = 'com')
   tempFile = NamedTemporaryFile(delete = False, suffix = '.mp3')
   tts.write_to_fp(tempFile)
   tempFile.flush()

   return tempFile.name

def generateSpeechText(question):
   if question.questionType == 'multiple-choice':
      return {'Wie sagt man' : 'de', question.question : 'en', 'auf Deutsch?': 'de'}
   
   if question.questionType == 'fill-in-the-blank':
      questionList = question.question.split('_')
      questionLeft = questionList[0]
      questionRight = questionList[1]
      #purely visual, but just wanted the original image in the design section to look the same

      return {questionLeft : 'de', '…' : 'de', questionRight : 'de'}
   
   if question.questionType == 'mouse-navigation':
      return {question.question : 'de'}
   
   return {question.question: 'en'}

def speakQuestion(dictionary, questionId):
   tempFiles = []
   outputDir = os.path.join(os.path.dirname(__name__), 'app', 'temp')
   os.makedirs(outputDir, exist_ok = True)
   #ensure the temporary directory exists
   combinedPath = os.path.join(outputDir, f'tempCombined{questionId}.mp3')

   try:
      audioClips = [AudioFileClip(tts(text, lang)) for text, lang in dictionary.items()]
      tempFiles = [clip.filename for clip in audioClips]

      combinedAudio = concatenate_audioclips(audioClips)
      combinedAudio.write_audiofile(combinedPath, codec = 'libmp3lame')

      print(f'file create at {os.path.abspath(combinedPath)}')
      
      combinedAudio.write_audiofile(combinedPath)
   
   finally:
      for file in tempFiles:
         try:
            os.remove(file)

         except OSError:
            pass

def generateJoke():
   messages = [
      "No matter how kind your children are, children in Germany will always be Kinder. ('Kinder' means children in German)",
      "Why did the German go to the bar? – Because he heard they had Bier-illiant drinks!",
      "What is the Wurst case scenario? – When we run out of sausages! ('Wurst' means sausage in German)",
      "I am in the Käse… or should I say, I am in the case of a sticky situation! ('Käse' means cheese in German)",
      "In Germany, there’s no such thing as a short drink – they all come in maßive sizes! ('maß' means measured or moderate in German)",
      "I asked my German friend for help with my car. He said, 'Let’s fix it with some Automatism! ('Auto' means car in German)'",
      "I asked my German friend whether he wanted a Gift. He put on a gas mask and said, 'Please don't poison me!' ('Gift' means poison in German)",
      "I tried to convice my Austrian painter friend that they can sell his paintings for a Billion. He said, 'You think that is worth more than Elon Musk?' ('billion' in German means trillion in English)",
      "I always tell my friend that she is very sensitive, and she always replies with: 'Dankeschön, its nice to know that I am sensibel.'"
   ]
   #these messages are generated by chat-GPT/ by myself

   return random.choice(messages)

def automatedMarking(result, duration):
   #must be noted that it would be flawed, if the user opens up a question but goes afk and gets it right after
   #duration should be a timedelta object
   score = 0

   if result == 'correct':
      score += 3

   if duration.total_seconds() < 10:
      score += 2
   
   elif duration.total_seconds() < 20:
      score += 1

   else:
      score += 0

   return score


def updateRecall(question, reviewData):
   #changed name from updateQuestion to updateRecall, since only the recall-related attributes are being updated
   question.interval = reviewData['interval']
   question.easiness = reviewData['easiness']

   if isinstance(reviewData['review_datetime'], str):
      question.date = datetime.fromisoformat(reviewData['review_datetime'])
   
   else:
      question.date = reviewData['review_datetime']

   question.repetitions = reviewData['repetitions']

def updateReview(question, quality):
   #question here will be an instance of the class
   reviewData = review(
      quality = quality,
      interval = question.interval,
      easiness = question.easiness,
      review_datetime = question.date,
      repetitions = question.repetitions
   )

   updateRecall(question, reviewData)

def firstReview(question, quality):
   reviewData = first_review(
      quality = quality,
      review_datetime = question.date
   )

   updateRecall(question, reviewData)

def decideQuestionXP(userQuestion):
   if userQuestion.easiness == 2.6:
      return 2
   
   else:
      return 0
   
def createAnswerList(answer):
   tempAnswer = answer.strip()
   answerList = re.findall(r'\w+|[^\w\s]', tempAnswer)
   #regex conditino here is just copied from GPT

   return answerList

def generateExtraBlocks(question, answerList):
   try:
      stream = client.chat.completions.create(
         model="gpt-4o-mini",  # Ensure you're using the correct model name
         messages=[
            {
               "role": "system",
               "content": """
               You are an algorithm for generating extra words to the correct answer for a multiple-choice question
               The choices of the question are the words that makeup the correct translation for the question.
               Give between 1 and 5 extra INCORRECT words or punctuation for the question that has been provided, for the user to choose from.
               DO NOT repeat the words that are given in the answerList
               Return the value as words separated by a comma in between.
               """
            },
            {
               "role": "user",
               "content": f"""
               The German sentence is: {question.question}
               This is a list of the correct blocks for this question: {answerList}.
               Generate between 1 and 5 extra incorrect blocks, that would make the question slightly harder for the person answering the question.
               """
            }
         ]
      )
      
      response = stream.choices[0].message.content
      responseList = response.split(',')

      concatenatedList = responseList + answerList
      finalList = [item.strip() for item in concatenatedList]
      #hahah sounds like finalist!
      #modified this, so no whitespace between options

      return finalList
   
   except Exception:
      return 'Error'
   
def generateWordOfTheDay():
   today = datetime.today().date()
   dailyWord = DailyWord.query.filter_by(date = today).first()

   if dailyWord:
      return dailyWord

   existingWords = [entry.word for entry in DailyWord.query.all()]
   existingWordsStr = ', '.join(existingWords)

   try:
      stream = client.chat.completions.create(
         model="gpt-4o-mini",  # Ensure you're using the correct model name
         messages=[
            {
               "role": "system",
               "content": f"""
                  - Be unique (not in the following list of words that have already been used: {existingWordsStr}),
                  – Provide a "German Word of the Day" for German language learners. The word should be:
                  1. A common or interesting word.
                  2. Suitable for beginners or intermediate learners.
                  3. Include the following details:
                     - The German word.
                     - The English translation.
                     - A simple sentence using the word in German with its English translation.
                     - A brief explanation or fun fact about the word, if possible.

                  Format the response as:
                  Word: [German word]
                  Translation: [English translation]
                  Sentence: [German sentence] ([English translation])
                  Fun Fact: [A short, interesting fact about the word, if any]
               """
            },
            {
               "role": "user",
               "content": f"""
               Give me a word of the day, that is unique and you find educational for German learners. This can be colloquial words or slang.
               Format the response specified below:
               
               Word: [German word]
               Translation: [English translation]
               Sentence: [German sentence] ([English translation])
               Fun Fact: [A short, interesting fact about the word, if any]
               """
            }
         ]
      )
      
      response = stream.choices[0].message.content.strip()

      word = None
      translation = None
      sentence = None
      fact = None

      lines = response.split('\n')
      for line in lines:
         if line.startswith("Word:"):
            word = line.split(":")[1].strip()
         elif line.startswith("Translation:"):
            translation = line.split(":")[1].strip()
         elif line.startswith("Sentence:"):
            sentence = line.split(":")[1].strip()
         elif line.startswith("Fun Fact:"):
            fact = line.split(":")[1].strip()

      newWord = DailyWord(word = word, translation = translation, sentence = sentence, fact = fact, date = today)

      return newWord
   
   except Exception:
      return 'Error'