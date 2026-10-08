import json, sys
sys.path.insert(0, sys.argv[1])
from th_cb import cb
tour = json.loads(sys.argv[2]); archs = json.loads(sys.argv[3]); placing = sys.argv[4]
out = cb("meta-matchup-data-store.data", [{"id": "meta-matchup-data-store", "property": "data"}],
         [{"id": "meta-tour-store", "property": "data", "value": tour},
          {"id": "meta-archetype-select", "property": "value", "value": archs},
          {"id": "meta-placing", "property": "value", "value": placing},
          {"id": "meta-result-rate", "property": "value", "value": "ignore_ties"}], changed=["meta-archetype-select.value"])
print(json.dumps(out))
