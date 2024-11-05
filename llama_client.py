import argparse
import requests
import json
import sys

def setup_argparse():
    parser = argparse.ArgumentParser(description='Generate text using Ollama')
    parser.add_argument('--prompt', type=str, required=True, help='Input prompt for the model')
    parser.add_argument('--model', type=str, default='llama2', help='Model to use (default: llama2)')
    return parser

def generate_text(prompt: str, model: str = 'llama2') -> str:
    """Generate text using Ollama API"""
    try:
        # Ollama runs on localhost:11434 by default
        url = 'http://localhost:11434/api/generate'
        
        # Prepare the request
        data = {
            'model': model,
            'prompt': prompt,
            'stream': False
        }
        
        print(f"Sending request to Ollama API with model: {model}")
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
        else:
            print(f"Error: API returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return ""
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Ollama. Please make sure Ollama is running.")
        print("Start Ollama by opening a new terminal and running: ollama run llama2")
        return ""
    except Exception as e:
        print(f"Error generating text: {str(e)}")
        return ""

def main():
    parser = setup_argparse()
    args = parser.parse_args()
    
    # First check if we can connect to Ollama
    try:
        requests.get('http://localhost:11434/api/version')
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Ollama.")
        print("Please make sure Ollama is running by:")
        print("1. Opening a new terminal")
        print("2. Running: ollama run llama2")
        sys.exit(1)
    
    # Generate text
    generated_text = generate_text(
        prompt=args.prompt,
        model=args.model
    )
    
    if generated_text:
        print("\nGenerated text:")
        print(generated_text)

if __name__ == "__main__":
    main()
