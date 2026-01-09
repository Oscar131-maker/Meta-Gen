import http.client
import json

def search_google(query, api_key):
    try:
        if not query:
            return {"error": "Query vacía"}

        # conn = http.client.HTTPSConnection("google.serper.dev")
        # payload = json.dumps({
        #     "q": query,
        #     "gl": "es",
        #     "hl": "es",
        #     "tbs": "qdr:m" # Filtro para el último mes
        # })
        
        # headers = {
        #     'X-API-KEY': api_key,
        #     'Content-Type': 'application/json'
        # }
        
        # conn.request("POST", "/search", payload, headers)
        # res = conn.getresponse()
        # data = res.read()
        
        # return json.loads(data.decode("utf-8"))

        # Refactoring to use requests for better readability/handling if I preferred, but sticking to http.client as per input script logic to be safe with user's specific logic.
        # Actually, let's just make sure it returns the dict.
        
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({
            "q": query,
            "gl": "es",
            "hl": "es",
            "tbs": "qdr:m" 
        })
        
        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
        
        conn.request("POST", "/search", payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        return json.loads(data.decode("utf-8"))

    except Exception as e:
        return {"error": str(e)}
