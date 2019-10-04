#!/usr/bin/python
'''
Run the script providing the slug of the project and the slug of the old and new resource.
The new resource should already have been created.
 
Example:
Old resource slug: 'old'
New resource slug: 'new'
 
python transifex-migrate-resource.py project old new
 
After running the command you will be asked for your Transifex username and password.
'''
# W.J. 2015 (license: MIT)
# Based on https://gist.github.com/mapapage/bb07703afaa4ea590109 by Marilena Papageorgiou 

from hashlib import md5
import requests
from requests.exceptions import RequestException
import json
import getpass
import sys


SERVER = "https://www.transifex.com"


def get_source_entity_hash(context, key):
    if isinstance(context, list):
        if context:
            keys = [key] + context
        else:
            keys = [key, '']
    else:
        if context:
            keys = [key, context]
        else:
            keys = [key, '']
    return str(md5(':'.join(keys).encode('utf-8')).hexdigest())


def migrate_resource(project, from_slug, to_slug, AUTH):
    headers = {'Content-type': 'application/json'}

    langs_url = "/api/2/project/%s/languages/" % project
    lang_entries = requests.get(
        SERVER + langs_url,
        headers=headers,
        auth=AUTH
    ).content
    lang_entries = json.loads(lang_entries)

    #lang_entries = [l for l in lang_entries if l['language_code']=='bg']

    for lang_entry in lang_entries:
        try:
            strings_url = "/api/2/project/%s/resource/%s/translation/%s/strings/"
            strings_from_url = strings_url % (
                project,
                from_slug,
                lang_entry['language_code']
            )

            strings_to_url = strings_url % (
                project,
                to_slug,
                lang_entry['language_code']
            )
            print "Reading language", lang_entry['language_code'], strings_from_url
            strings = requests.get(
                SERVER + strings_from_url + "?details",
                headers=headers,
                auth=AUTH
            ).content

            reviewed = list()
            strings_new = []
            for elem in json.loads(strings):
                # skip empty translations
                translation_is_empty = False
                if elem['pluralized']:
                    for k,v in elem['translation'].items():
                        if not v:
                            translation_is_empty = True
                else:
                    translation_is_empt = not elem['translation']
                if translation_is_empty:
                    continue
                # process entry for re-submit
                del elem["user"]
                context = elem["context"]
                key = elem["key"]

                source_entity_hash = get_source_entity_hash(
                    context, key
                )

                elem["source_entity_hash"] = source_entity_hash
                if elem["reviewed"]:
                    reviewed.append(elem)
                    elem["reviewed"] = False

                strings_new.append(elem)
            strings = strings_new
            if not strings:
                print "No translations - skipping"
                continue

            print "Putting language", lang_entry['language_code'], strings_to_url
            response = requests.put(
                SERVER + strings_to_url,
                data=json.dumps(strings),
                headers=headers,
                auth=AUTH
            )
            response.raise_for_status()
            if reviewed:
                s = [{
                    "source_entity_hash": elem["source_entity_hash"],
                    "translation": elem["translation"],
                    "reviewed": True
                } for elem in reviewed]

                print "Putting review statuses for language", lang_entry['language_code']
                response = requests.put(
                    SERVER + strings_to_url,
                    data=json.dumps(s),
                    headers=headers,
                    auth=AUTH
                )
                response.raise_for_status()

        except RequestException as e:
            msg = "HTTP ERROR %s occurred for the resource in the language %s. Reason: " % (
                response.status_code,
                lang_entry["language_code"]
            )
            error_msg = msg + response.text
            print(error_msg)

        except Exception, e:
            error_msg = 'Unknown exception caught: %s' % (
                unicode(e)).encode('utf-8')
            print(error_msg)


def run():

    if not len(sys.argv) == 4:
        print "You should do: python script_name.py <project> <resource_from> <resource_to>"
        sys.exit()

    #from_project: the slug of the old project
    #to_project: the slug of the new project
    project = sys.argv[1]
    from_resource = sys.argv[2]
    to_resource = sys.argv[3]

    username = raw_input("What's your Transifex username?")
    pwd = getpass.getpass(prompt="..and your Transifex password?")

    # Your Transifex credentials
    # TODO: parse from ~/.transifexrc
    AUTH = (username, pwd)

    migrate_resource(project, from_resource, to_resource, AUTH)

if __name__ == '__main__':
    run()
