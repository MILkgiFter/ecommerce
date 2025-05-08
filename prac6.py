import json
from pymongo import MongoClient
from bson import ObjectId

# Подключение к MongoDB
uri = "mongodb+srv://dik:diko@cluster0.7tkxp.mongodb.net/web_logs?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client['ecomercedatabase']  # Замените на имя вашей базы данных
collection = db['products']

# Открытие и загрузка данных из JSON файла
with open("products.json", "r", encoding="utf-8") as file:
    products = json.load(file)

# Преобразование _id в ObjectId и загрузка в коллекцию
for product in products:
    product["_id"] = ObjectId(product["_id"]["$oid"])

# Вставка продуктов в коллекцию
collection.insert_many(products)

print("Данные успешно загружены в MongoDB")