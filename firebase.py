import firebase_admin
from firebase_admin import credentials, firestore


cred = credentials.Certificate("free-tools-466817-firebase-adminsdk-fbsvc-c77929d905.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

def save_event(data):
    try:
        db.collection("events").add(data)
        print("-"*100)
        print("╰(*°▽°*)╯已將資料儲存到Firebase.")
    except Exception as e:
        print(f"Error saving event: {e}")
def save_message_id(message_id):
    try:
        db.collection("message_ids").document(message_id).set({})
        print("-"*100)
        print("╰(*°▽°*)╯已將訊息ID儲存到Firebase.")
    except Exception as e:
        print(f"Error saving message ID: {e}")
def is_saved(message_id):
    doc = db.collection("message_ids").document(message_id).get()
    return doc.exists
        
    