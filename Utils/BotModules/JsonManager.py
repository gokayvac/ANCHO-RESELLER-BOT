import json
import os

class JsonManager:
    @staticmethod
    def load_json(file_path, default_content):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            JsonManager.save_json(file_path, default_content)
            return default_content

    @staticmethod 
    def save_json(file_path, data):
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def ensure_json_files():
        os.makedirs('JSON', exist_ok=True)
        files = {
            'JSON/Bot.json': {"prefix": "!", "token": "", "admin_ids": []},
            'JSON/Data.json': {"resellers": []},
            'JSON/Products.json': {"products": []}
        }
        for file_path, default_content in files.items():
            if not os.path.exists(file_path):
                JsonManager.save_json(file_path, default_content)
            else:
                try:
                    with open(file_path, 'r') as f:
                        json.load(f)
                except json.JSONDecodeError:
                    JsonManager.save_json(file_path, default_content)

    @staticmethod
    def is_reseller(user_id):
        try:
            with open('JSON/Data.json', 'r') as f:
                data = json.load(f)
                return any(str(user_id) == r['discord_id'] for r in data['resellers'])
        except (FileNotFoundError, json.JSONDecodeError):
            return False