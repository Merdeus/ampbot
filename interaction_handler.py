from flask import Flask, request, jsonify
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import json
import asyncio
from config import PUBLIC_KEY, CLIENT_ID
from database import Database

app = Flask(__name__)
db_instance = None
bot_instance = None

def set_db_instance(db):
    global db_instance
    db_instance = db_instance or db

def set_bot_instance(bot):
    global bot_instance
    bot_instance = bot_instance or bot

def verify_signature(request_body: bytes, signature: str, timestamp: str) -> bool:
    if not PUBLIC_KEY:
        return False
    
    try:
        verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))
        verify_key.verify(
            f'{timestamp}{request_body}'.encode(),
            bytes.fromhex(signature)
        )
        return True
    except BadSignatureError:
        return False

@app.route('/interactions', methods=['POST'])
def handle_interaction():
    signature = request.headers.get('X-Signature-Ed25519')
    timestamp = request.headers.get('X-Signature-Timestamp')
    request_body = request.data
    
    if not verify_signature(request_body, signature, timestamp):
        return jsonify({'error': 'Invalid signature'}), 401
    
    interaction_data = json.loads(request_body)
    
    if interaction_data['type'] == 1:
        return jsonify({'type': 1})
    
    if interaction_data['type'] == 2:
        command_name = interaction_data['data']['name']
        user_id = int(interaction_data['member']['user']['id']) if 'member' in interaction_data else int(interaction_data['user']['id'])
        
        if command_name == 'history':
            options = {opt['name']: opt['value'] for opt in interaction_data['data'].get('options', [])}
            user_id_filter = options.get('user')
            limit = options.get('limit', 20)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                from bot import get_history_embed
                user = None
                if user_id_filter and bot_instance:
                    try:
                        user_obj = loop.run_until_complete(bot_instance.fetch_user(user_id_filter))
                        user = user_obj
                    except:
                        pass
                
                embed, history_entries = loop.run_until_complete(get_history_embed(user, limit))
                
                if embed:
                    embed_dict = {
                        'title': embed.title,
                        'description': embed.description,
                        'color': embed.color.value if embed.color else None,
                        'type': 'rich'
                    }
                    return jsonify({
                        'type': 4,
                        'data': {
                            'embeds': [embed_dict]
                        }
                    })
                else:
                    message = f"No history entries found for <@{user_id_filter}>" if user_id_filter else "No history entries found"
                    return jsonify({
                        'type': 4,
                        'data': {
                            'content': message,
                            'flags': 64
                        }
                    })
            finally:
                loop.close()
        
        return jsonify({
            'type': 4,
            'data': {
                'content': f'Command {command_name} is not yet implemented for user-installed apps'
            }
        })
    
    return jsonify({'error': 'Unknown interaction type'}), 400

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

