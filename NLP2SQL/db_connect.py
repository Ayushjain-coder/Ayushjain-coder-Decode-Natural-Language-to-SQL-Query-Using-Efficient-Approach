import string, nltk
import speech_recognition as sr
import pyttsx3
import pywhatkit
import datetime
import wikipedia    
from googletrans import Translator
from textblob import TextBlob
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from flask import Flask,render_template, request
from flask_mysqldb import MySQL
from word2number import w2n
 
app = Flask(__name__)
 
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'student'
 
mysql = MySQL(app)

listener = sr.Recognizer()
engine = pyttsx3.init()

def isHindi(text):
    lang = TextBlob(text)

    if lang.detect_language() == 'hi':
        return True
    # return False    

def hin_to_eng(text):

    translator = Translator()

    text_to_translate = translator.translate(text, src= 'hi', dest= 'en')
    
    text = text_to_translate.text

    return text

def iswordNumber(n):
  try: 
    w2n.word_to_num(n)
    return 1
  except ValueError:
    return 0    

def query_solver(query):
    query = query.lower()

    for c in string.punctuation:
        query = query.replace(c,"")

    query = word_tokenize(query)
    
    stop = stopwords.words('english')
    
    l = ['and','or','not','between','more']
    
    stop = [i for i in stop if i not in l]

    final_query = []

    for i in query:
      if i not in stop:
        final_query.append(i)    

    le = WordNetLemmatizer()

    for i,word in enumerate(final_query):
      if word not in ['less','more']:
        final_query[i] = le.lemmatize(word)

    tagged = nltk.pos_tag(final_query)
    
    final_tagged = []
    
    for i in tagged:
      if i[1] not in ['VBZ','WP$']:
        final_tagged.append(i)          

    return tagged         

@app.route('/')
def form():
	return render_template('form.html')

@app.route('/take_command', methods = ['POST'])
def take_command():
    try:
        with sr.Microphone() as source:
            print('listening...')
            voice = listener.listen(source)
            command = listener.recognize_google(voice)

            if isHindi(command):
                command = hin_to_eng(command) 

            if 'alexa' in command:
                command = command.replace('alexa', '')
                print(command)      
    except:
        pass

    return render_template("form.html", command = command)      

@app.route('/query_data', methods = ['POST'])
def query_data():

    if request.method == 'POST':

        try:
            query = request.form['nlp_query']

            if isHindi(query):
                query = hin_to_eng(query)

            print(query)    

            cursor = mysql.connection.cursor()

            query = query_solver(query)

            print(query)

            query_list = [i[0] for i in query]

            l = []
            d = {'ORDER BY':0,'flag_student':0,'flag_book':0}
            t = {'studentdetails':0,'bookdetails':0}
            f = {'studentdetails':'studentdetails AS s','bookdetails':'bookdetails AS b','studentname':'s.studentname','studentrollno':'s.studentrollno','studentmarks':'s.studentmarks','studentaddress':'s.studentaddress','bookisbn':'b.bookisbn','bookprice':'b.bookprice','booktitle':'b.booktitle','bookauthor':'b.bookauthor'}
            all_tables = ['studentname','studentrollno','studentmarks','studentaddress','bookisbn','booktitle','bookprice','bookauthor']
            from_tables = []

            # print(query_list)

            for i,word in enumerate(query_list):
              if word in 'id':
                l.append('id')
              elif word in 'count':
                l.append('COUNT')
              elif word in 'average':
                l.append('AVG')
              elif word in ['sum','add']:
                l.append('SUM')
              elif word in ['minimum','min']:
                l.append('MIN')
              elif word in ['maximum','max']:
                l.append('MAX')    
              elif word in ['more','greater'] and 'equal' in query_list[i+1:]:
                l.append('>=') 
              elif word in ['more','greater']:
                l.append('>')   
              elif word in ['smaller','less'] and 'equal' in query_list[i+1:]:
                l.append('<=')  
              elif word in ['smaller','less']:
                l.append('<')
              elif word in 'not' and 'equal' in query_list[i+1:]:
                l.append('<>')  
              elif word in ['between','range']:
                l.append('BETWEEN')
              elif word in ['first','top']:
                l.append('LIMIT')           
              elif word in 'name' and (query_list[i-1] in 'student' or query_list[i+1] in 'student'):  
                l.append('studentname')
                t['studentdetails'] = 1
                d['flag_student'] = 1
              elif word in ['rollno','roll']:
                l.append('studentrollno')
              elif word in ['mark','point']:
                l.append('studentmarks')
                t['studentdetails'] = 1
                d['flag_student'] = 1
              elif word in 'address':
                l.append('studentaddress')
                t['studentdetails'] = 1
                d['flag_student'] = 1
              elif word in ['isbn','id']:  
                l.append('bookisbn')
                t['bookdetails'] = 1
                d['flag_book'] = 1
              elif word in ['title','name'] and (query_list[i-1] in 'book' or query_list[i+1] in 'book'):
                l.append('booktitle')
                t['bookdetails'] = 1
                d['flag_book'] = 1
              elif word in ['rate','price']:
                l.append('bookprice')
                t['bookdetails'] = 1
                d['flag_book'] = 1
              elif word in 'author':
                l.append('bookauthor')
                t['bookdetails'] = 1
                d['flag_book'] = 1      
              elif word in ['increasing','assending'] and l[len(l)-1] in all_tables:
                j = len(l)
                l[j-1] = [l[j-1],'ASC']
              elif word in ['decreasing','desending'] and l[len(l)-1] in all_tables:
                j = len(l)
                l[j-1] = [l[j-1],'DESC']      
              elif word.isdigit() and l[len(l)-1] in all_tables:
                j = len(l)
                l[j-1] = [l[j-1],word]
              elif word.isdigit() and l[len(l)-1] in ['>','>=','<','<=','<>']:
                j = len(l)
                l[j-1] = [l[j-2],l[j-1],word]
                del l[j-2]
              elif word in ['and'] and l[len(l)-2] in 'BETWEEN' and l[len(l)-1].isdigit() and query_list[i+1].isdigit():
                l.append('and'.upper())
                j = len(l)
                l[j-4] = [l[j-4],l[j-3],l[j-2],l[j-1],query_list[i+1]]
                del l[j-3:j]
                del query_list[i+1]  
              elif iswordNumber(word) and l[len(l)-1] in 'LIMIT':
                j = len(l)
                l[j-1] = [l[j-1],str(w2n.word_to_num(word))]  
              elif word.isdigit() and type(l[len(l)-1]) is not list:
                l.append(word)          
              elif word in ['and','or'] and type(l[len(l)-1]) is list and 'ASC' not in l[len(l)-1] and 'DESC' not in l[len(l)-1]:
                j = len(l)
                l[j-1].append(word)
              else:  
                pass

            if 'studentrollno' in l: 
                if d['flag_student'] == 1 and d['flag_book'] == 0:
                    t['studentdetails'] = 1
                
                if d['flag_student'] == 0 and d['flag_book'] == 1:
                    t['bookdetails'] = 1

                if d['flag_student'] == 1 and d['flag_book'] == 1:
                    t['studentdetails'] = 1
                    t['bookdetails'] = 1                    


            actual_tables = [key for key in t.keys() if t[key] == 1]

            from_tables.append(" INNER JOIN ".join(actual_tables)) 

            if len(actual_tables) > 1:
              from_tables.append("ON s.studentrollno = b.studentrollno")

            select_st = []
            where_st = []

            for i in l:
              if type(i) is not list:
                  select_st.append(i)
              elif i[0] in 'LIMIT':
                  where_st.append(' '.join(i))  
              elif i[1] in ['>','>=','<','<=','<>']:
                  where_st.append(' '.join(i))
              elif i[1] in 'BETWEEN':
                  where_st.append(' '.join(i))
              elif i[1] in ['ASC','DESC']:
                  if d['ORDER BY'] == 0:
                    where_st.append('ORDER BY '+' '.join(i))
                    d['ORDER BY'] = 1
                  else:  
                    where_st.append(' '.join(i))        
              else:  
                    where_st.append(i[0] + ' = ' + i[1])            

            if 'COUNT' in select_st:
                (sql,select_st) = sql_fun('COUNT',select_st,where_st,tables)
            elif 'AVG' in select_st:
                (sql,select_st) = sql_fun('AVG',select_st,where_st,tables)
            elif 'SUM' in select_st:
                (sql,select_st) = sql_fun('SUM',select_st,where_st,tables)
            elif 'MAX' in select_st:
                (sql,select_st) = sql_fun('MAX',select_st,where_st,tables)
            elif 'MIN' in select_st:
                (sql,select_st) = sql_fun('MIN',select_st,where_st,tables)        
            elif len(where_st) == 0:            
                sql = 'SELECT ' + ", ".join(select_st) + ' FROM ' + " ".join(from_tables)
            else:
                k = [i for i in where_st if 'ASC' not in i and 'DESC' not in i and 'LIMIT' not in i]
                if len(k) > 0:
                  k[0] = ' WHERE '+ k[0]
                sql = 'SELECT ' + ", ".join(select_st) + ' FROM ' + " ".join(from_tables) +" ".join(k) + " " + ", ".join([i for i in where_st if 'ASC' in i or 'DESC' in i or 'LIMIT' in i])                     

            if 'INNER JOIN' in sql:
                for key,value in f.items():
                    sql = sql.replace(key,value)
                sql = sql.replace("s.s.","s.")         
                sql = sql.replace("b.s.","b.")    

            print(select_st)
            print(where_st)
            print(from_tables)
            print(sql)           

            data = [1,sql]

            print(data)
            
            cursor.execute(sql)    

            data.append([i[0] for i in cursor.description])
            
            data.extend(cursor.fetchall())

            mysql.connection.commit()

            cursor.close()

        except:
            data = [0]

        return render_template("display.html", len = len(data), data = data)                    		

app.run(host='localhost', port=8080)        