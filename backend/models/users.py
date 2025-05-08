from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
import bcrypt

# MongoDB connection setup
uri = "mongodb+srv://dik:diko@cluster0.7tkxp.mongodb.net/web_logs?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client['ecomercedatabase']  # Замените на имя вашей базы данных


class User:
    def __init__(self, username, password, first_name='', last_name='', email='', phone='', gender='', city=''):
        self._id = ObjectId()  # Automatically generate ObjectId
        self.username = username
        self.password = password  # Store the hashed password
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.gender = gender
        self.city = city
        self.created_at = datetime.utcnow()  # Set current time for account creation

    def to_dict(self):
        """Convert the user object to a dictionary for JSON serialization."""
        return {
            "_id": str(self._id),  # Convert ObjectId to string
            "username": self.username,
            "password": self.password,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "gender": self.gender,
            "city": self.city,
            "created_at": self.created_at.isoformat()  # Convert datetime to ISO 8601 string
        }

    @staticmethod
    def from_dict(data):
        """Create a User object from a dictionary."""
        return User(
            username=data["username"],
            password=data["password"],
            first_name=data.get("first_name", ''),
            last_name=data.get("last_name", ''),
            email=data.get("email", ''),
            phone=data.get("phone", ''),
            gender=data.get("gender", ''),
            city=data.get("city", '')
        )

    @staticmethod
    def register(username, password):
        """Register a new user."""
        if db.users.find_one({'username': username}):
            return None  # User already exists

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        new_user = User(username=username, password=hashed_password)

        # Вставка пользователя в базу данных
        db.users.insert_one(new_user.to_dict())  # Вставляем объект пользователя в базу данных
        return new_user  # Возвращаем созданный объект пользователя

    @staticmethod
    def login(username, password):
        """Login user and return user object if successful."""
        user = db.users.find_one({'username': username})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            return User.from_dict(user)  # Return User object if login is successful
        return None  # Return None if login failed

    @staticmethod
    def update_user(username, update_data):
        """Update user information."""
        valid_keys = ['first_name', 'last_name', 'email', 'phone', 'gender', 'city']
        filtered_data = {key: value for key, value in update_data.items() if key in valid_keys}

        if filtered_data:
            result = db.users.update_one(
                {'username': username},
                {'$set': filtered_data}
            )
            return result.modified_count > 0  # Return True if a user was updated
        return False

    @staticmethod
    def delete_user(username):
        """Delete a user by their username."""
        result = db.users.delete_one({'username': username})
        return result.deleted_count > 0  # Return True if a user was deleted
