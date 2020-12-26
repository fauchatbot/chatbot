from datetime import datetime, date
import spacy
from io import StringIO
from dictionaries import dictionary,dict_list_bereinigt, list_pm, list_socialmedia, list_technologiemanagement, klausur_fragen
from xml.dom.minidom import parse as makeDomObjFromFile, parseString as makeDomObjFromString
import urllib
from textblob_de import TextBlobDE as TextBlob
from textblob_de import PatternParser
from textblob_de.packages import pattern_de as pd
import wikipedia
from similarity.jarowinkler import JaroWinkler
from wikipedia.exceptions import DisambiguationError
import requests
from bs4 import BeautifulSoup as soup
import lxml
import re
import os
import random
import json
from flask import Flask, jsonify, request, redirect, url_for
import nltk



nltk.download('punkt')

app = Flask(__name__)
port = int(os.environ["PORT"])

@app.route('/', methods=['POST'])
def index():
    return 'Home Page'

@app.route('/wikipedia', methods=['GET','POST'])
def wikipedia_search():
    if request.method == 'POST':
        wikipedia.set_lang("de")
        data = json.loads(request.get_data())
        # print(data)        
        nlp = spacy.load('de_core_news_sm')
        doc = nlp(data['nlp']['source'])
        suchwort = []

        for token in doc:
            if token.tag_ in ['NE','NNE', 'NN']:
                suchwort.append(token.text)

        suchwort = ' '.join(suchwort)

        print(suchwort)
        try:
            wikipediaseite = wikipedia.page(suchwort)
            answer = 'Wikipedia sagt: '
            answer += wikipedia.summary(suchwort, sentences=5) + " Weiterlesen? " + wikipediaseite.url
            # replies=[{ 
            #   'type': 'text', 
            #   'content': answer,
            # }]
            # return replies
            return jsonify( 
            status=200, 
            replies=[{ 
              'type': 'text', 
              'content': answer,
            }], 
            conversation={ 
              'memory': { 'key': 'value' } 
            } 
          )
            
        except wikipedia.exceptions.DisambiguationError as e:
            # replies=[{ 
            #   'type': 'text', 
            #   'content': "Wikipedia sagt: Ich konnte leider keinen Eintrag zu dem Wort '"+suchwort+"' finden. Vielleicht meinst du eins der folgenden Worte "+ str(e.options)+"? Wenn ja, gib deine Frage nochmal mit dem richtigen Wort ein.",
            # }]
            # return replies
            return e.options
            return jsonify( 
            status=200, 
            replies=[{ 
              'type': 'text', 
              'content': "Ich konnte leider keinen Eintrag zu dem Wort '"+suchwort+"' finden. Vielleicht meinst du eins der folgenden Worte "+ str(e.options)+"? Wenn ja, gib deine Frage nochmal mit dem richtigen Wort ein.",
            }], 
            conversation={ 
              'memory': { 'key': 'value' } 
            } 
          )
    else:
        return '<h1>Wrong Address, go back to home!</h1>'        
        

@app.route('/wetter', methods=['POST'])
def wetter():

    api_address='http://api.openweathermap.org/data/2.5/weather?appid=0c42f7f6b53b244c78a418f4f181282a&q='
    data = json.loads(request.get_data())
    # print(data)

    city = data["nlp"]["entities"]["location"][0]['raw']
    # city = input('City Name:')
    # city = 'Berlin'
    url = api_address + city
    json_data = requests.get(url).json()
    #print(json_data )
    aktuelletemperatur = str(json_data["main"]["temp"]-273.15)
    höchsttemperatur = str(json_data["main"]["temp_max"]-273.15)
    windgeschwindigkeit= str(json_data["wind"]["speed"])

    return jsonify( 
            status=200, 
            replies=[{ 
            'type': 'text', 
            # 'content':city,
            'content': "Die aktuelle Temperatur in "+ city+ " beträgt "+aktuelletemperatur [0:4] + " C°. Die Tageshöchstemperatur wird " + höchsttemperatur [0:4]+ " C° nicht übersteigen. Der Wind weht mit einer Geschwindigkeit von " + windgeschwindigkeit+" km/h.",
            }], 
            conversation={ 
            'memory': { 'key': 'value' } 
            } 
        )

@app.route('/news')
def news():
    encoding=None
    extracttags={"title":"no title","link":None,"description":"no description"}
    dom_obj = makeDomObjFromFile(urllib.request.urlopen("http://www.tagesschau.de/newsticker.rdf"))
    news = []

    for item in dom_obj.getElementsByTagName("item"):
        extracted_item={}
        for tag in extracttags:
            try:
                text=""
                for node in item.getElementsByTagName(tag)[0].childNodes:
                    if node.nodeType == node.TEXT_NODE:
                        text += node.data
                assert text != ""
            except (IndexError,AssertionError):
                extracted_item[tag]=extracttags[tag]
            else:
                if encoding:
                    text=text.encode(encoding)
                extracted_item[tag]=text
        news.append(extracted_item)

    sentences = ''
    if len(news)>=5:
        for i in range (0,3):
            sentences += "Neues in der Welt:" + '\n' + news[i]['title'] + '\n' + news[i]['description'] + '\n' + news[i]['link'] + '\n'
    else:
        for i in range (0,len(news)):
            sentences += "Neues in der Welt:" + '\n' + news[i]['title'] + '\n' + news[i]['description'] + '\n' + news[i]['link'] + '\n'

    return jsonify( 
            status=200, 
            replies=[{ 
            'type': 'text', 
            'content':sentences,
            }], 
            conversation={ 
            'memory': { 'key': 'value' } 
            } 
        )

@app.route('/mensa')
def mensa():
    weekdays = {6:'Sonntag', 0:'Monntag', 1:'Dienstag', 2:'Mittwoch', 3:'Donnerstag', 4:'Freitag', 5:'Samstag'}
    datetime.today().weekday()
    heute_tag = weekdays[datetime.today().weekday()]
    heute_zeit = date.today().strftime("%d.%m.%Y")

    result = requests.get('https://www.werkswelt.de/index.php?id=isch')
    text = soup(result.content, 'lxml')
    final_text = text.findAll("div", {"style": 'background-color:#ecf0f1;border-radius: 4px 4px 0px 0px; padding: 8px;'})[0].get_text()
    txt = re.sub('[\n\r\xa0]', '', final_text)
    txt = re.sub(' +', ' ',txt)
    txt = re.split('Essen [1-9]', txt)
    del txt[0]
    essen_list = [{"type": "list", "content": {"elements":[]}}]
    intermediate_list = [{"title": "Speiseplan " + heute_tag + " " + heute_zeit ,"imageUrl": "","subtitle": "","buttons": []}]

    for i in enumerate(txt,1):
        myd =  {
                "title": "",
                "imageUrl": "",
                "subtitle": "",
                "buttons": []
              }
        myd['title'] = 'Essen ' + str(i[0])
        myd['subtitle'] = i[1]
        intermediate_list.append(myd)

    print(intermediate_list)
    essen_list[0]['content']['elements'] = intermediate_list
    # print(essen_list)
    return jsonify( 
    status=200, 
    replies=essen_list, 
    conversation={ 
      'memory': { 'key': 'value' } 
    } 
  )

@app.route('/search', methods=['POST'])
def search():
    global result
    result = []
    data = json.loads(request.get_data())
    jarowinkler = JaroWinkler()
    page_list = []
    suchwort = []
    first_set = []
    second_set = []

    # nlp = spacy.load('de_core_news_sm')
    nlp = spacy.load('de_core_news_sm')
    # nlp = spacy.load('en_core_web_sm', disable=["parser",'ner'])

    word = ' '.join([i.capitalize() for i in data['nlp']['source'].split(' ')])
    doc = nlp(word)
    for token in doc:
        # if token.tag_ in ['NNP','NNPS', 'NN', 'NNS']:
        if token.tag_ in ['NE','NNE', 'NN']:
            suchwort.append(token.text)
        
    print(word)
    if suchwort:
        if len(suchwort) >= 2:

            for d in dict_list_bereinigt:
                for key, value in d.items():
                    for i in value:
                        if jarowinkler.similarity(i.lower(), suchwort[-1].lower()) > 0.95:
                            first_set.append(key)

            for d in dict_list_bereinigt:
                for key, value in d.items():
                    for i in value:
                        if jarowinkler.similarity(i.lower(), suchwort[-2].lower()) > 0.95:
                            second_set.append(key)
            found_pages = list(set(first_set).intersection(set(second_set)))
        else:
            for d in dict_list_bereinigt:
                for key, value in d.items():
                    for i in value:
                        if jarowinkler.similarity(i.lower(), suchwort[-1].lower()) > 0.95:
                            first_set.append(key)
            found_pages = first_set

        searchlist = list(set(found_pages))
        page_list = [int(i[0]) for i in [i.split('.') for i in searchlist]]
        sentence = "Außerdem habe {} Seite(n) im Skript mit {} finden können".format(len(page_list),' '.join(suchwort))  
        pic_urls = [dictionary[sorted(searchlist)[i]] for i in range(0,len(searchlist),3)]    
        result.append({'type': 'text', 'content':sentence + ". Hier sind ein paar Beispiele " + " ".join(str(i) for i in sorted(page_list))})

        for i in pic_urls:
            myd = {'type': 'picture','content':''}
            myd['content'] = i
            result.append(myd)
            
    if len(page_list) == 0:
        result = [{'type': 'text','content': 'Ich konnte nichts im Skript zum Wort {} finden'.format(suchwort[0])}]

    replies=result
    # return replies
    return jsonify( 
    status=200, 
    replies=result, 
    conversation={ 
      'memory': { 'key': 'value' } 
    } 
  )

@app.route('/zeit')
def zeit():
    now = str(datetime.now()).split(' ')[1].split('.')[0][:5]
    time_str = 'Je noch dem wo du gerade bist... \n In Nürnberg ist es gerade {}'.format(now)
    return jsonify( 
            status=200, 
            replies=[{ 
            'type': 'text', 
            'content':time_str,
            }], 
            conversation={ 
            'memory': { 'key': 'value' } 
            } 
        )
@app.route('/abfrage_klausur', methods=['POST'])
def abfrage_klausur():
    #data = json.loads(request.get_data())
    #print(data['nlp'])
    global result
    result = []
    index_frage=int(random.randint(0,38)*2) 
    index_antwort=int(index_frage+1)
    myd_frage={"":""}
    myd_antwort={"":""}
    myd_frage = {'type': 'picture','content':'','delay': 5}
    myd_frage['content'] = klausur_fragen[index_frage]
    myd_antwort = {'type': 'picture','content':'','delay':1 }
    myd_antwort['content'] = klausur_fragen[index_antwort]

    result.append(myd_frage)
    antwort={'content': 'Die richtige Antwortet lautet', 'type': 'text','delay':5}
    result.append(antwort)
    result.append(myd_antwort)
        
    replies=result
    # return replies
    return jsonify( 
    status=200, 
    replies=result, 
    conversation={ 
      'memory': { 'key': 'value' } 
    } 
  )
@app.route('/abfrage', methods=['GET','POST'])
def abfrage():
    #data = json.loads(request.get_data())
    #print(data['nlp'])
    global result
    result = []
    data = json.loads(request.get_data())
    print(data["nlp"])
    print(data['conversation']['memory']['thema']['raw'])
    thema=data['conversation']['memory']['thema']['raw'] # thema
    anzahl_fragen=int(data['nlp']['source'])
    for i in range(anzahl_fragen):
        if thema in ['Projektmanagement','projektmanagement','projectmanagement']:
            index_frage=int(random.randint(0,31)*2) 
            index_antwort=int(index_frage+1)
            myd_frage={"":""}
            myd_antwort={"":""}
            myd_frage = {'type': 'picture','content':'','delay': 5}
            myd_frage['content'] = list_pm[index_frage]
            myd_antwort = {'type': 'picture','content':'','delay': 4}
            myd_antwort['content'] = list_pm[index_antwort]

            result.append(myd_frage)
            antwort={'content': 'Die Antwortet lautet', 'type': 'text','delay':5}
            result.append(antwort)
            result.append(myd_antwort)
        if thema in ['socialmedia','Socialmedia','SocialMedia','SocialMedia']:
            index_frage=int(random.randint(0,38)*2) 
            index_antwort=int(index_frage+1)
            myd_frage={"":""}
            myd_antwort={"":""}
            myd_frage = {'type': 'picture','content':'','delay': 5}
            myd_frage['content'] = list_socialmedia[index_frage]
            myd_antwort = {'type': 'picture','content':'','delay': 4}
            myd_antwort['content'] = list_socialmedia[index_antwort]

            result.append(myd_frage)
            antwort={'content': 'Die Antwortet lautet', 'type': 'text','delay':5}
            result.append(antwort)
            result.append(myd_antwort)
        if thema in ['Technologiemanagement','technologiemanagement','TechnologieManagement']:
            index_frage=int(random.randint(0,29)*2) 
            index_antwort=int(index_frage+1)
            myd_frage={"":""}
            myd_antwort={"":""}
            myd_frage = {'type': 'picture','content':'','delay': 5}
            myd_frage['content'] = list_technologiemanagement[index_frage]
            myd_antwort = {'type': 'picture','content':'','delay': 4}
            myd_antwort['content'] = list_technologiemanagement[index_antwort]

            result.append(myd_frage)
            antwort={'content': 'Die Antwortet lautet', 'type': 'text','delay':5}
            result.append(antwort)
            result.append(myd_antwort)
    replies=result
    # return replies
    return jsonify( 
    status=200, 
    replies=result, 
    conversation={ 
      'memory': { 'key': 'value' } 
    } 
  )


@app.route('/abfrage_oleg')
def abfrage_oleg():
    
    # return replies
    return jsonify( 
    status=200, 
    replies= [{'content': {'elements': [{'buttons': [],
     'imageUrl': '',
     'subtitle': '',
     'title': 'Welches Startup hat laut dem Wall Street Journal 2018 die höchste Bewertung ?'},
    {'buttons': [], 'imageUrl': '', 'subtitle': 'Uber', 'title': ''},
    {'buttons': [], 'imageUrl': '', 'subtitle': 'Airbnb', 'title': ''},
    {'buttons': [], 'imageUrl': '', 'subtitle': 'SpaceX', 'title': ''},
    {'buttons': [], 'imageUrl': '', 'subtitle': 'Didi Chuxing', 'title': ''}]},
  'delay': 5,
  'type': 'list'},
 {'content': 'RWelches Startup hat laut dem Wall Street Journal 2018 die höchste Bewertung ?: a)Uber b)SpaceX c)Airbnb d) Didi Chuxing', 'type': 'text'},
 {'content': {'elements': [{'buttons': [],
     'imageUrl': '',
     'subtitle': '',
     'title': 'Welche Merkmale unterscheiden ein Startup von einer gewöhnlichen Gründung?'},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': ' Innovationsgrad der Geschäftsidee und das Wachstumspotential ',
     'title': ''},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': 'Größe des Gründerteams und die Finanzierungsart der Gründung',
     'title': ''},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': 'der Onlineauftritt und die Vertriebskanäle',
     'title': ''},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': 'es gibt keine wesentlichen Unterschiede',
     'title': ''}]},
  'delay': 0,
  'type': 'list'},
 {'content': 'Richtige Antwort: Uber', 'type': 'text'},
 {'content': {'elements': [{'buttons': [],
     'imageUrl': '',
     'subtitle': '',
     'title': 'Welche Merkmale unterscheiden ein Startup von einer gewöhnlichen Gründung?'},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': ' Innovationsgrad der Geschäftsidee und das Wachstumspotential ',
     'title': ''},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': 'Größe des Gründerteams und die Finanzierungsart der Gründung',
     'title': ''},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': 'der Onlineauftritt und die Vertriebskanäle',
     'title': ''},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': 'es gibt keine wesentlichen Unterschiede',
     'title': ''}]},
  'delay': 0,
  'type': 'list'},
 {'content': 'Richtige Antwort: Uber', 'type': 'text'},
 {'content': 'Richtige Antwort: Uber', 'type': 'text'},
 {'content': {'elements': [{'buttons': [],
     'imageUrl': '',
     'subtitle': '',
     'title': 'Welche Merkmale unterscheiden ein Startup von einer gewöhnlichen Gründung?'},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': ' Innovationsgrad der Geschäftsidee und das Wachstumspotential ',
     'title': ''},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': 'Größe des Gründerteams und die Finanzierungsart der Gründung',
     'title': ''},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': 'der Onlineauftritt und die Vertriebskanäle',
     'title': ''},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': 'es gibt keine wesentlichen Unterschiede',
     'title': ''}]},
  'delay': 0,
  'type': 'list'},
 {'content': 'Richtige Antwort:  Innovationsgrad der Geschäftsidee und das Wachstumspotential',
  'type': 'text'},
 {'content': {'elements': [{'buttons': [],
     'imageUrl': '',
     'subtitle': '',
     'title': 'Was versteht man unter einem Unicorn Startup?'},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': 'Ein privates Unternehmen, welches das Potential hat ein börsennotiertes Unternehmen zu werden.',
     'title': ''},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': 'Ein privates Unternehmen mit einer Bewertung über 1 Mrd. USD.',
     'title': ''},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': 'Ein börsennotiertes Unternehmen, das vor weniger als 5 Jahren gegründet worden ist.',
     'title': ''},
    {'buttons': [],
     'imageUrl': '',
     'subtitle': 'Ein junges börsennotiertes Unternehmen, das Umsätze über Mrd. USD erwirtschaftet.',
     'title': ''}]},
  'delay': 0,
  'type': 'list'},
 {'content': 'Richtige Antwort: Ein privates Unternehmen mit einer Bewertung über 1 Mrd. USD.',
  'type': 'text'}], 
    conversation={ 
      'memory': { 'key': 'value' } 
    } 
  )



# @app.route('/skript_and_wiki_search', methods=['POST'])
# def skript_and_wiki_search():

#     data = json.loads(request.get_data())
    
#     print(wikipedia_search())
#     print(search())
#     result = wikipedia_search() + search()
#     return jsonify( 
#             status=200, 
#             replies=result, 
#             conversation={ 
#               'memory': { 'key': 'value' } 
#             })
    # return 'Hello wordl'

    # if search():
    #     return jsonify( 
    #     status=200, 
    #       replies=result, 
    #     conversation={ 
    #       'memory': { 'key': 'value' } 
    #     }) 
    # else:
    #     return redirect(url_for('wikipedia_search'), code=307)


@app.route('/errors',methods=['POST'])
def errors():
    print(json.loads(request.get_data()))
    return jsonify(status=200)

app.run(port=port,host="0.0.0.0")


@app.route('/lecture-search', methods=['POST'])
def lecture_search():

	global result
	result = []
    site_result = ['https://filehorst.de/d/djCzzslt', 
    'https://filehorst.de/d/dqrouGAl',
	'https://filehorst.de/d/dEtaCcxf',
	'https://filehorst.de/d/dgFFbjHi',
	'https://filehorst.de/d/dihAJgFo',
	'https://filehorst.de/d/dcfhdnlh',
	'https://filehorst.de/d/dujbxqiJ',
	'https://filehorst.de/d/dyielhbu',
	'https://filehorst.de/d/dozterIh',
	'https://filehorst.de/d/dBJdDxjz',
	'https://filehorst.de/d/drewBtzk',
	'https://filehorst.de/d/drqGxlkn',
	'https://filehorst.de/d/drspwjFG',
	'https://filehorst.de/d/dqvrDGzG',
	'https://filehorst.de/d/dbivbevB',
	'https://filehorst.de/d/dIIepgdA',
	'https://filehorst.de/d/dghCqCHJ',
	'https://filehorst.de/d/dqnFhipz']

	
    for i in site_result:
		dict_result = {'type': 'text','content':''}
		dict_result['content'] = i
		result.append(dict_result)
	

	replies=result
    # return replies
    return jsonify( 
    status=200, 
    replies=result, 
    conversation={ 
      'memory': { 'key': 'value' } 
    } 
  )
