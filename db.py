from pymongo import MongoClient
from bson.objectid import ObjectId

# Connect to local MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['chat_email_db']

# Collections shared between Member 1 and Member 2
users = db['users']
conversations = db['conversations']
messages = db['messages']
emails = db['emails']

def to_id(id_val):
    """Safely convert string or ObjectId"""
    try:
        return ObjectId(id_val)
    except:
        return id_val
