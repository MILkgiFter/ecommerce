from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
uri = "mongodb+srv://dik:diko@cluster0.7tkxp.mongodb.net/web_logs?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client['ecomercedatabase']

class Product:
    def __init__(self, name, description, price, category, likes=0, views=0, quantity=0, created_at=None):
        self._id = ObjectId()  # Automatically generate ObjectId
        self.name = name
        self.description = description
        self.price = price
        self.category = category
        self.likes = likes
        self.views = views
        self.quantity = quantity
        self.created_at = created_at if created_at else datetime.utcnow()  # Set current time if not provided

    def to_dict(self):
        """Convert the product object to a dictionary for JSON serialization."""
        return {
            "_id": str(self._id),  # Convert ObjectId to string
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "category": self.category,
            "likes": self.likes,
            "views": self.views,
            "quantity": self.quantity,
            "created_at": self.created_at.isoformat()  # Convert datetime to ISO 8601 string
        }

    @staticmethod
    def from_dict(data):
        """Create a Product object from a dictionary."""
        return Product(
            name=data["name"],
            description=data["description"],
            price=data["price"],
            category=data["category"],
            likes=data.get("likes", 0),
            views=data.get("views", 0),
            quantity=data.get("quantity", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else None
        )

    @staticmethod
    def delete_product(product_id):
        """Delete a product by its ID."""
        result = db.products.delete_one({'_id': ObjectId(product_id)})
        return result.deleted_count > 0  # Return True if a product was deleted

    @staticmethod
    def update_product(product_id, update_data):
        """Update product information."""
        # Ensure update_data contains valid keys
        valid_keys = ['name', 'description', 'price', 'category', 'likes', 'views', 'quantity']
        filtered_data = {key: value for key, value in update_data.items() if key in valid_keys}

        if filtered_data:
            result = db.products.update_one(
                {'_id': ObjectId(product_id)},
                {'$set': filtered_data}
            )
            return result.modified_count > 0  # Return True if a product was updated
        return False
