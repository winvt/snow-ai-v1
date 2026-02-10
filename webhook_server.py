#!/usr/bin/env python3
"""
Simple webhook server to capture LINE group ID
Run this, then send a message to your group chat
"""

from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle LINE webhook events"""
    try:
        data = request.get_json()
        print("=== WEBHOOK EVENT ===")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Extract group ID if it's a group message
        if 'events' in data:
            for event in data['events']:
                if event.get('type') == 'message':
                    source = event.get('source', {})
                    if source.get('type') == 'group':
                        group_id = source.get('groupId')
                        print(f"\n🎉 GROUP ID FOUND: {group_id}")
                        print(f"Use this as your LINE_RECIPIENT_ID: {group_id}")
                        return jsonify({'status': 'success', 'groupId': group_id})
        
        return jsonify({'status': 'received'})
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print("🚀 Starting webhook server...")
    print("1. Add your bot to a group chat")
    print("2. Send any message in the group")
    print("3. Look for the GROUP ID in the output below")
    print("4. Press Ctrl+C to stop")
    print("-" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
