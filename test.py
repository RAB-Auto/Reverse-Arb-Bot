import requests

def get_fractional_share_list():
    url = "https://api.tradier.com/v1/markets/fractionals"
    headers = {
        "Authorization": "Bearer uqRPzpGVQaYGFJypWdLdaFqam32G",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        fractionals = data.get("fractionals", [])
        
        if fractionals:
            print("Fractional Share List:")
            for fractional in fractionals:
                print(f"Symbol: {fractional['symbol']}, Description: {fractional['description']}")
        else:
            print("No fractional shares available.")
    else:
        print(f"Failed to retrieve fractional shares. Status code: {response.status_code}")

# Call the function
get_fractional_share_list()