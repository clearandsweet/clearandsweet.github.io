import json, sys, urllib.request
def cb(output, outputs, inputs, state=None, changed=None):
    body = {"output": output, "outputs": outputs, "inputs": inputs, "state": state or [],
            "changedPropIds": changed or []}
    req = urllib.request.Request("https://www.trainerhill.com/_dash-update-component", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=300).read().decode())
if __name__ == "__main__":
    tour = json.loads(sys.argv[1])
    out = cb("..meta-archetype-select.options...meta-archetype-store.data..",
             [{"id": "meta-archetype-select", "property": "options"}, {"id": "meta-archetype-store", "property": "data"}],
             [{"id": "meta-tour-store", "property": "data", "value": tour}], changed=["meta-tour-store.data"])
    print(json.dumps(out))
