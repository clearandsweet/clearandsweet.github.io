import json, sys, urllib.request
path = sys.argv[1]; search = sys.argv[2] if len(sys.argv) > 2 else ""
body = {"output": ".._pages_content.children..._pages_store.data..",
        "outputs": [{"id": "_pages_content", "property": "children"}, {"id": "_pages_store", "property": "data"}],
        "inputs": [{"id": "_pages_location", "property": "pathname", "value": path},
                   {"id": "_pages_location", "property": "search", "value": search}],
        "changedPropIds": ["_pages_location.pathname"], "state": []}
req = urllib.request.Request("https://www.trainerhill.com/_dash-update-component", data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
print(urllib.request.urlopen(req, timeout=120).read().decode())
