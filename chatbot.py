from io import StringIO
from dictionaries import dictionary,dict_list_bereinigt
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
import json
from flask import Flask, jsonify, request, redirect, url_for
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
    text = soup(result.content, 'lxml')
    final_text = text.findAll("div", {"style": 'background-color:#ecf0f1;border-radius: 4px 4px 0px 0px; padding: 8px;'})[0].get_text()
    txt = re.sub('[\n\r\xa0]', '', final_text)
    txt = re.sub(' +', ' ',txt)
    txt = re.split('Essen [1-9]', txt)
    essen_list = [{"type": "list", "content": {"elements":[]} }]
    intermediate_list = []

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

# @app.route('/search', methods=['POST'])
def search():
    global result
    result = []
    data = json.loads(request.get_data())
    jarowinkler = JaroWinkler() 

    if re.findall(r'"\s*(.*?)\s*"', data['nlp']['source']):
        searchword = re.findall(r'"\s*(.*?)\s*"', data['nlp']['source'])[0].split(' ')
        print(searchword)
        # print(data['nlp']['source'])
        first_set = []
        second_set = []
        if len(searchword) > 1:
            
            for d in dict_list_bereinigt:
                for key, value in d.items():
                    for i in value:
                        if jarowinkler.similarity(i.lower(), searchword[0].lower()) > 0.95:
                            first_set.append(key)

            for d in dict_list_bereinigt:
                for key, value in d.items():
                    for i in value:
                        if jarowinkler.similarity(i.lower(), searchword[1].lower()) > 0.95:
                            second_set.append(key)
            found_pages = list(set(first_set).intersection(set(second_set)))
        else:
            for d in dict_list_bereinigt:
                for key, value in d.items():
                    for i in value:
                        if jarowinkler.similarity(i.lower(), searchword[0].lower()) > 0.95:
                            first_set.append(key)
            found_pages = first_set

        result = []
        searchlist = list(set(found_pages))
        page_list = [int(i[0]) for i in [i.split('.') for i in searchlist]]
        sentence = "Ich habe {} Seite(n) im Skript mit {} finden können".format(len(page_list),searchword)  
        pic_urls = [dictionary[sorted(searchlist)[i]] for i in range(0,len(searchlist),3)]    
        result.append({'type': 'text', 'content':sentence + ". Hier sind ein paar Beispiele " + " ".join(str(i) for i in sorted(page_list))})

        for i in pic_urls:
            myd = {'type': 'picture','content':''}
            myd['content'] = i
            result.append(myd)
        
    if len(page_list) == 0:
        result = False

    return result
    # return jsonify( 
    # status=200, 
    # replies=result, 
    # conversation={ 
    #   'memory': { 'key': 'value' } 
    # } 
  # )

@app.route('/skript_and_wiki_search', methods=['POST'])
def skript_and_wiki_search():

    data = json.loads(request.get_data())
    search()

    if search():
        return jsonify( 
        status=200, 
          replies=result, 
        conversation={ 
          'memory': { 'key': 'value' } 
        }) 
    else:
        return redirect(url_for('wikipedia_search'()))


@app.route('/errors', methods=['POST'])
def errors():
    print(json.loads(request.get_data()))
    return jsonify(status=200)

app.run(port=port,host="0.0.0.0")