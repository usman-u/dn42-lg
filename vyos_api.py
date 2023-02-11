import requests
import json

class vyos_api:
    def __init__(self, url, key):
        self.url=url
        self.key=key
    
    def get_bgp_peers(self):
        query = f'''
    {{
        ShowNeighborsBgp 
        (data: 
            {{
                key: "{self.key}", 
                family: "inet"
            }}
        ) 
        {{
            success
            errors
            data {{ result }}
        }}
    }}
'''
        r = requests.post(self.url, json={'query': query}, verify=False)
        result =  json.loads(r.text)
        return result["data"]["ShowNeighborsBgp"]["data"]["result"]["peers"]
    

    def get_bgp_peer(self, peer_ip):
        query = f'''{{
            ShowNeighborsBgp (data: 
                {{
                    key: "{self.key}", 
                    family: "inet"
                    peer: "{peer_ip}"
                }}
                        ) 
                        {{
                            success
                            errors
                            data {{ result }}
                        }}
                    }}
'''
        r = requests.post(self.url, json={'query': query}, verify=False)
        result =  json.loads(r.text)
        return result["data"]["ShowNeighborsBgp"]["data"]["result"]

    def get_all_routes(self, family="inet"):
        query = f'''{{
            ShowRoute (data: 
                {{
                    key: "{self.key}", 
                    family: "{family}"
                }}
                        ) 
                        {{
                            success
                            errors
                            data {{ result }}
                        }}
                    }}
'''
        r = requests.post(self.url, json={'query': query}, verify=False)
        result =  json.loads(r.text)
        return result["data"]["ShowRoute"]["data"]["result"]


    def get_route_summary(self, family="inet"):
        query = f'''{{
            ShowSummaryRoute (data: 
                {{
                    key: "{self.key}", 
                    family: "{family}"
                }}
                        ) 
                        {{
                            success
                            errors
                            data {{ result }}
                        }}
                    }}
'''
        r = requests.post(self.url, json={'query': query}, verify=False)
        result =  json.loads(r.text)
        return result["data"]["ShowSummaryRoute"]["data"]["result"]

# fr_lil1 = vyos_api("https://10.100.100.4/graphql", "4ubVxjaAB9vDz7WrDSwJJ6K4h")
# print(fr_lil1.get_bgp_peers())
# print("---")
# print(fr_lil1.get_bgp_peer("fe80::ade0"))
# print("---")
# print(fr_lil1.get_route_summary("inet"))
# print("---")
# print(fr_lil1.get_route_summary("inet6"))
# print(fr_lil1.get_all_routes("inet6"))