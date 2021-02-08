'''
Access to github metadata as exported by ghrip (https://github.com/zw/ghrip).
'''
import json

class GhMeta:
    def __init__(self, paths):
        self.paths = paths

    def __getitem__(self, idx):
        (repo, pull) = idx
        base = self.paths[repo]

        filename = f'{base}/issues/{pull//100}xx/{pull}.json'
        try:
            with open(filename, 'r') as f:
                data0 = json.load(f)
        except IOError as e:
            raise KeyError

        filename = f'{base}/issues/{pull//100}xx/{pull}-PR.json'
        try:
            with open(filename, 'r') as f:
                data1 = json.load(f)
        except IOError as e:
            data1 = None

        data0['pr'] = data1
        return data0

    def get(self, pull, default=None):
        try:
            return self[pull]
        except KeyError:
            return default
