import requests
import json
import re

def ask_llm(prompt):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            },
            timeout=60
        )
        result = response.json()
        return result.get("response", "No response from LLM")
    except requests.exceptions.Timeout:
        return "Request timed out"
    except Exception as e:
        return f"Error: {e}"

def safe_json_parse(s):
    try:
        return json.loads(s)
    except:
        match = re.search(r'\{[^{}]*\}', s)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
    return {}