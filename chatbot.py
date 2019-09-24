import os
import json
from flask import Flask, jsonify, request

app = Flask(__name__)
port = int(os.environ["PORT"])

@app.route('/', methods=['POST'])
def index():
    return 'Home Page'

@app.route('/wikipedia', methods=['POST'])
def wikipedia_search():
    from textblob_de import TextBlobDE as TextBlob
    from textblob_de import PatternParser
    from textblob_de.packages import pattern_de as pd
    import wikipedia
    from similarity.jarowinkler import JaroWinkler
    from wikipedia.exceptions import DisambiguationError
    import nltk
    nltk.download('punkt')

    wikipedia.set_lang("de")
    blob = TextBlob("Where is Baku?")
    liste= blob.tags
    for l in liste:
        if l[1]=="NN":
            nomen=l[0]
        
    print(nomen)
    suchwort=nomen


    try:
        wikipediaseite = wikipedia.page(suchwort)
        answer = wikipedia.summary(suchwort, sentences=5)+" Weiterlesen? "+ wikipediaseite.url
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
        



@app.route('/errors', methods=['POST'])
def errors():
    print(json.loads(request.get_data()))
    return jsonify(status=200)

app.run(port=port,host="0.0.0.0")