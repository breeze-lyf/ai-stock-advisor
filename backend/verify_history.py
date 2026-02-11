import requests

def verify_history():
    ticker = "002050" # The one that failed in the logs
    url = f"http://127.0.0.1:8000/api/stocks/{ticker}/history"
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Retrieved {len(data)} bars.")
            if len(data) > 0:
                last_bar = data[-1]
                print(f"Last bar indicators: RSI={last_bar.get('rsi')}, MACD={last_bar.get('macd')}, BB_Upper={last_bar.get('bb_upper')}")
        else:
            print(f"Failed with: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_history()
