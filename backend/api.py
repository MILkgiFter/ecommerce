import os

from bson import ObjectId
from flask import Flask, jsonify, request, render_template, redirect, url_for, session, Response
from pymongo import MongoClient
from datetime import datetime

from pymongo import ASCENDING

from werkzeug.security import generate_password_hash, check_password_hash
import bcrypt
import secrets
import json
try:
    from models.users import User
    from models.products import Product
except ImportError:
    # Если файлы еще не перемещены
    pass

app = Flask(__name__)
cart = []

# Подключение к MongoDB через переменную окружения или дефолтное значение
uri = os.environ.get('MONGO_URI', "mongodb+srv://dik:diko@cluster0.7tkxp.mongodb.net/web_logs?retryWrites=true&w=majority")
client = MongoClient(uri)
db = client['ecomercedatabase']  # Замените на имя вашей базы данных

def get_current_user_id():
    return session.get('username')  # Returns None if not logged in

def init_db():
    # Создаем коллекции, если их нет
    if 'carts' not in db.list_collection_names():
        db.create_collection('carts')
    if 'orders' not in db.list_collection_names():
        db.create_collection('orders')
    if 'user_behaviors' not in db.list_collection_names():
        db.create_collection('user_behaviors')

# Инициализируем базу данных
init_db()
app.secret_key = 'my_super_secret_key_123456'
db.products.update_many(
    {"likes": {"$exists": False}},
    {"$set": {"likes": 0}}
)
def add_viewed_product(username, product_id):
    db.user_behaviors.update_one(
        {"username": username},
        {"$addToSet": {"viewed_products": product_id}},
        upsert=True
    )


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/auth', methods=['GET'])
def auth():
    return render_template('auth.html')


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    # Поиск пользователя в базе данных
    user = db.users.find_one({'username': username})

    # Проверка наличия пользователя и соответствия пароля
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        # Сохраняем информацию о пользователе в сессии
        session['username'] = username
        session['user_id'] = str(user['_id'])  # ID пользователя
        session['logged_in'] = True  # Флаг авторизации

        return redirect(url_for('index'))

    # Возврат сообщения об ошибке
    return "Неправильное имя пользователя или пароль", 401



@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']

    # Хэшируем пароль перед сохранением
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    db.users.insert_one({  # Изменено на db.users
        'username': username,
        'password': hashed_password,
        'first_name': '',
        'last_name': '',
        'email': '',
        'phone': '',
        'gender': '',
        'city': ''
    })

    return redirect(url_for('auth'))  # Перенаправляем на страницу входа


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)  # Удалите username из сессии
    return redirect(url_for('auth'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        gender = request.form['gender']
        city = request.form['city']

        db.users.update_one(
            {'username': session['username']},
            {'$set': {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'gender': gender,
                'city': city
            }}
        )
        return redirect(url_for('profile'))

    user = db.users.find_one({'username': session['username']})
    return render_template('profile.html', user=user)


@app.route('/delete_profile', methods=['POST'])
def delete_profile():
    db.users.delete_one({'username': session['username']})  # Удаление пользователя
    session.clear()  # Очистка сессии
    return redirect(url_for('index'))




@app.route('/products', methods=['GET'])
def get_products():
    # Получаем параметры фильтрации из запроса
    category = request.args.get('category')
    min_views = request.args.get('min_views', type=int)
    search_query = request.args.get('search')

    # Базовый запрос для поиска продуктов
    query = {}

    # Добавляем фильтр по категории, если указано
    if category:
        query['category'] = category

    # Добавляем фильтр по просмотрам, если указано
    if min_views is not None:
        query['views'] = {'$gte': min_views}

    # Добавляем поиск по имени, если указан поисковый запрос
    if search_query:
        query['name'] = {'$regex': search_query, '$options': 'i'}  # Регистронезависимый поиск

    # Выполняем запрос с учетом фильтров
    products = list(db.products.find(query))
    for product in products:
        product['_id'] = str(product['_id'])  # Преобразуем ObjectId в строку

    # Получаем все уникальные категории для фильтрации
    categories = db.products.distinct('category')

    return render_template('products.html', products=products, categories=categories)




@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        # Получаем данные из формы
        new_product = {
            'name': request.form['name'],
            'description': request.form['description'],
            'price': float(request.form['price']),
            'category': request.form['category'],
            'image_url': request.form['image_url']
        }
        # Сохраняем продукт в базе данных
        db.products.insert_one(new_product)
        return redirect(url_for('add_product'))  # Перенаправляем на ту же страницу для добавления следующего продукта

    # Отображаем все продукты на странице добавления
    products = list(db.products.find())
    return render_template('add_product.html', products=products)

# Маршрут для редактирования продуктов
@app.route('/edit_product/<product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = db.products.find_one({'_id': ObjectId(product_id)})

    if request.method == 'POST':
        # Обновляем продукт в базе данных
        db.products.update_one(
            {'_id': ObjectId(product_id)},
            {'$set': {
                'name': request.form['name'],
                'description': request.form['description'],
                'price': float(request.form['price']),
                'category': request.form['category'],
                'image_url': request.form['image_url']
            }}
        )
        return redirect(url_for('add_product'))  # Перенаправляем обратно к списку продуктов

    return render_template('edit_product.html', product=product)

# Маршрут для удаления продуктов
@app.route('/delete_product/<product_id>', methods=['POST'])
def delete_product(product_id):
    db.products.delete_one({'_id': ObjectId(product_id)})
    return redirect(url_for('add_product'))  # Возвращаемся к списку после удаления

@app.route('/product/<product_id>')
def view_product(product_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth'))  # Redirect to login if user is not logged in

    product = db.products.find_one({"_id": ObjectId(product_id)})
    recommendations = get_user_recommendations(user_id)  # текущий ID пользователя

    if product:
        # Record the view interaction in user_interactions collection
        db.user_interactions.insert_one({
            "user_id": user_id,
            "product_id": product_id,
            "interaction_type": "view"
        })

        # Optional: Update view count in the products collection for display purposes
        new_views_count = product.get('views', 0) + 1
        db.products.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {"views": new_views_count}}
        )
        product['views'] = new_views_count  # Update local view count for template display

        return render_template('product_detail.html', product=product, recommendations=recommendations)
    else:
        return "Product not found", 404



@app.route('/like_product/<product_id>', methods=['POST'])
def like_product(product_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth'))

    # Record the like interaction in user_interactions collection
    db.user_interactions.insert_one({
        "user_id": user_id,
        "product_id": product_id,
        "interaction_type": "like"
    })

    # Optional: Update like count in the products collection for display purposes
    db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$inc": {"likes": 1}}  # Increment the like count
    )

    return redirect(url_for('view_product', product_id=product_id))


def get_user_recommendations(user_id):
    # Find most viewed or liked products by the user
    pipeline = [
        {"$match": {"user_id": user_id, "interaction_type": {"$in": ["view", "like"]}}},
        {"$group": {"_id": "$product_id", "interaction_count": {"$sum": 1}}},
        {"$sort": {"interaction_count": -1}},
        {"$limit": 5}  # Limit to top 5 most interacted products
    ]

    recommendations = db.user_interactions.aggregate(pipeline)

    # Fetch product details for each recommended product
    recommended_products = []
    for recommendation in recommendations:
        product = db.products.find_one({"_id": ObjectId(recommendation['_id'])})
        if product:
            recommended_products.append(product)

    return recommended_products


@app.route('/add_to_cart/<product_id>', methods=['POST'])
def add_to_cart(product_id):
    username = get_current_user_id()

    if not username:
        return {"message": "Пожалуйста, войдите в систему"}, 401  # Unauthorized

    try:
        # Convert product_id to ObjectId
        product_id_obj = ObjectId(product_id)
    except Exception as e:
        return {"message": "Неверный формат ID товара"}, 400  # Bad Request

    # Fetch product details to get the name
    product = db.products.find_one({"_id": product_id_obj})  # Use ObjectId here
    if not product:
        return {"message": "not found"}, 404  # Product not found

    cart = db.carts.find_one({"username": username})

    if cart is None:
        # If the cart does not exist, create a new one with the product name
        db.carts.insert_one({
            "username": username,
            "items": [{
                "product_id": product_id,
                "product_name": product['name'],  # Store product name
                "quantity": 1
            }]
        })
    else:
        # Initialize a flag to track if the product was found
        product_found = False

        # Check if the product already exists in the cart
        for item in cart['items']:
            if item['product_id'] == product_id:
                item['quantity'] += 1  # Increment quantity
                product_found = True
                break

        if not product_found:
            # If the product is not found, append it with the name and quantity 1
            cart['items'].append({
                "product_id": product_id,
                "product_name": product['name'],  # Store product name
                "quantity": 1
            })

        # Update the cart in the database
        db.carts.update_one(
            {"username": username},
            {"$set": {"items": cart['items']}}
        )

    return {"message": "added"}, 200




@app.route('/cart')
def view_cart():
    username = session.get('username')

    if not username:
        return redirect(url_for('auth'))

    cart = db.carts.find_one({"username": username})

    # Debugging output
    print("Username:", username)
    print("Cart Data:", cart)

    if cart and 'items' in cart:
        products = cart['items']  # No need to query the products collection again

        # Calculate total cost
        total_cost = 0
        for item in products:
            # Assuming you also have a way to get the price of each product
            product = db.products.find_one({"_id": ObjectId(item['product_id'])})  # Fetch product details
            if product:
                item['product_name'] = product['name']  # Add product name
                total_cost += product['price'] * item['quantity']  # Calculate cost

        # Additional debugging
        print("Products Data:", products)
        print("Total Cost:", total_cost)

    else:
        products = []
        total_cost = 0
        print("Cart is empty or does not have items.")

    return render_template('cart.html', products=products, total_cost=total_cost)



@app.route('/remove_from_cart/<product_id>', methods=['POST'])
def remove_from_cart(product_id):
    # Get the username from the session to identify the user's cart
    username = session.get('username')

    if not username:
        return jsonify({"message": "Пожалуйста, войдите в систему"}), 401  # Unauthorized

    # Convert the product_id to ObjectId to ensure it matches the format in MongoDB
    product_object_id = ObjectId(product_id)

    # Find the user's cart
    cart = db.carts.find_one({"username": username})

    if cart and product_object_id in cart['items']:
        # Remove the product from the 'items' list
        cart['items'].remove(product_object_id)
        db.carts.update_one(
            {"username": username},
            {"$set": {"items": cart['items']}}
        )
        return jsonify({"message": "Товар удален из корзины"}), 200
    else:
        return jsonify({"message": "Товар не найден в корзине"}), 404



@app.route('/checkout/<user_id>', methods=['POST'])
def checkout(user_id):
    cart = db.carts.find_one({'user_id': user_id})
    if cart:
        products = cart.get('products', [])
        db.orders.insert_one({
            'user_id': user_id,
            'products': products,
            'timestamp': datetime.now()
        })
        db.carts.delete_one({'user_id': user_id})
        return jsonify({'message': 'Order has been placed'})
    return jsonify({'message': 'Cart is empty'})

@app.route('/orders/<user_id>', methods=['GET'])
def get_orders(user_id):
    orders = list(db.orders.find({'user_id': user_id}, {'_id': 0}))
    return render_template('orders.html', user_id=user_id, orders=orders)

@app.route('/recommendations/<user_id>', methods=['GET'])
def recommendations_page(user_id):
    user_cart = db.carts.find_one({'user_id': user_id})
    if user_cart:
        product_ids = user_cart.get('products', [])
        recommendations = list(db.products.find({'_id': {'$nin': product_ids}}, {'_id': 0}).limit(5))
        return render_template('recommendations.html', user_id=user_id, recommendations=recommendations)
    return render_template('recommendations.html', user_id=user_id, recommendations=[])

if __name__ == '__main__':
    # Запуск приложения на всех интерфейсах (для работы в Docker)
    app.run(host='0.0.0.0', port=5000, debug=True)

