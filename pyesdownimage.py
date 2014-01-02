#!/usr/bin/env python

import traceback, yaml, urllib2, os, io
from pyes import ES
from pyes.query import MatchAllQuery, FilteredQuery
from pyes.filters import ExistsFilter, ANDFilter, NotFilter
from PIL import Image
from time import sleep

setting_file = open("settings.yml", 'r')
settings =  yaml.load(setting_file)
conn = ES(settings['es_config']['url']+':'+settings['es_config']['port'])

def download_images():
    for index in settings['es_index']:
        for doc_type in index['doc_type']:
            treat_doc_type(index, doc_type)
 
def treat_doc_type(index, doc_type):
    counter = 0
    for field in doc_type['fields']:
        counter += 1
        filters = [
            ExistsFilter(field['from']),
            NotFilter(ExistsFilter(field['to']))
            ]
        q = FilteredQuery(MatchAllQuery(), ANDFilter(filters))
        docs = conn.search(index=index['name'], doc_type=doc_type['name'], query=q, fields=field['from'], sort='date:desc')
        for doc in docs:
            doc_id =  doc._meta.id
            directory = doc_id[0:1]+'/'+doc_id[1:2]+'/'+doc_id[2:3]+'/'+doc_id+'/'+field['to']+'/'
            filename = str(counter)+'.jpg'
            image_url = doc[field['from']]
            images = []
            for image in field['images']:
                new_url = treat_image(image_url, image, directory, filename)
                images.append({image['name']: new_url})
            new_document = {field['to']: images }
            reindex(doc_id, index['name'], doc_type['name'], new_document)

def treat_image(image_url, image_data, directory, filename):
    img_file = io.BytesIO(urllib2.urlopen(image_url).read())
    img_original = Image.open(img_file)
    img_result = img_original
    size = image_data['width'], image_data['height']
    if (image_data['width']):
        img_result.thumbnail(size, Image.ANTIALIAS)
    complete_path = settings['media_directory']+'/'+directory+image_data['name']+'-'+filename
    if not os.path.exists(settings['media_directory']+'/'+directory):
        os.makedirs(settings['media_directory']+'/'+directory)
    img_result.save(complete_path, 'JPEG', quality=image_data['quality'])
    return settings['media_url']+directory+image_data['name']+'-'+filename

def reindex(doc_id, index, doc_type, document):
    conn.update(index=index, doc_type=doc_type, id=doc_id, document=document)

while True:
    download_images()
    sleep(settings['interval'])
