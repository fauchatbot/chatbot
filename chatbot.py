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
import re
import os
import json
from flask import Flask, jsonify, request
import nltk
nltk.download('punkt')

app = Flask(__name__)
port = int(os.environ["PORT"])

@app.route('/', methods=['POST'])
def index():
    return 'Home Page'

@app.route('/wikipedia', methods=['POST'])
def wikipedia_search():

    nomen = 'Not Found Page'
    data = json.loads(request.get_data())
    wikipedia.set_lang("de")
    blob = TextBlob(data['nlp']['source'])
    liste= blob.tags
    for l in liste:
        if l[1] in ['NN', 'FW', 'NNS', 'NNP', 'NNPS']:
            nomen = l[0]
        
    # print(nomen)
    suchwort = nomen

    try:
        wikipediaseite = wikipedia.page(suchwort)
        answer = wikipedia.summary(suchwort, sentences=5) + " Weiterlesen? " + wikipediaseite.url
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
    result = requests.get('https://www.werkswelt.de/index.php?id=isch')
    text = soup(result.content)
    final_text = text.findAll("div", {"style": 'background-color:#ecf0f1;border-radius: 4px 4px 0px 0px; padding: 8px;'})[0].get_text()
    txt = re.sub('[\n\r\xa0]', '', final_text)
    txt = re.sub(' +', ' ',txt)
    txt = re.split('Essen [1-9]', txt)
    essen_list = ''
    for i in txt:
        essen_list += i + ' '
        # essen_list.append(i)

    print(essen_list)
    return jsonify( 
    status=200, 
    replies=[{ 
      'type': 'text', 
      'content': essen_list,
    }], 
    conversation={ 
      'memory': { 'key': 'value' } 
    } 
  )



@app.route('/errors', methods=['POST'])
def errors():
    print(json.loads(request.get_data()))
    return jsonify(status=200)

app.run(port=port,host="0.0.0.0")