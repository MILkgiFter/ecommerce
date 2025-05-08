from bson import ObjectId
from flask import Flask, jsonify, request, render_template, redirect, url_for, session, Response
from pymongo import MongoClient
from datetime import datetime
from pymongo import ASCENDING
from werkzeug.security import generate_password_hash, check_password_hash
import bcrypt
import secrets
import json

# Import Flask-RESTx for Swagger documentation
from flask_restx import Api, Resource, fields, Namespace
from bson import ObjectId
from flask import Flask, jsonify, request, render_template, redirect, url_for, session, Response
from pymongo import MongoClient
from datetime import datetime

from pymongo import ASCENDING

from werkzeug.security import generate_password_hash, check_password_hash
import bcrypt
import secrets
import json

app = Flask(__name__)
cart = []

# Initialize Swagger with Flask-RESTx
authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}

api = Api(app, version='1.0', title='E-Commerce API',
          description='A simple e-commerce API',
          doc='/swagger',
          authorizations=authorizations)

# Create namespaces for different resource groups
auth_ns = api.namespace('auth', description='Authentication operations')
product_ns = api.namespace('products', description='Product operations')
cart_ns = api.namespace('cart', description='Cart operations')
order_ns = api.namespace('orders', description='Order operations')
user_ns = api.namespace('users', description='User operations')

# Подключение к MongoDB
uri = "mongodb+srv://dik:diko@cluster0.7tkxp.mongodb.net/web_logs?retryWrites=true&w=majority"
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

# Define backend for Swagger documentation
user_model = api.model('User', {
    'username': fields.String(required=True, description='Username'),
    'password': fields.String(required=True, description='Password'),
    'first_name': fields.String(description='First name'),
    'last_name': fields.String(description='Last name'),
    'email': fields.String(description='Email address'),
    'phone': fields.String(description='Phone number'),
    'gender': fields.String(description='Gender'),
    'city': fields.String(description='City')
})

login_model = api.model('Login', {
    'username': fields.String(required=True, description='Username'),
    'password': fields.String(required=True, description='Password')
})

product_model = api.model('Product', {
    'name': fields.String(required=True, description='Product name'),
    'description': fields.String(required=True, description='Product description'),
    'price': fields.Float(required=True, description='Product price'),
    'category': fields.String(required=True, description='Product category'),
    'image_url': fields.String(required=True, description='Product image URL'),
    'views': fields.Integer(description='Number of views'),
    'likes': fields.Integer(description='Number of likes')
})

cart_item_model = api.model('CartItem', {
    'product_id': fields.String(required=True, description='Product ID'),
    'product_name': fields.String(required=True, description='Product name'),
    'quantity': fields.Integer(required=True, description='Quantity')
})

cart_model = api.model('Cart', {
    'username': fields.String(required=True, description='Username'),
    'items': fields.List(fields.Nested(cart_item_model), description='Cart items')
})

order_model = api.model('Order', {
    'user_id': fields.String(required=True, description='User ID'),
    'products': fields.List(fields.String, description='List of product IDs'),
    'timestamp': fields.DateTime(description='Order timestamp')
})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth', methods=['GET'])
def auth():
    return render_template('auth.html')

@auth_ns.route('/login')
class LoginResource(Resource):
    @api.doc('login_user', body=login_model)
    def post(self):
        """Login a user"""
        if request.method == 'POST':
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

@auth_ns.route('/register')
class RegisterResource(Resource):
    @api.doc('register_user', body=user_model)
    def post(self):
        """Register a new user"""
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            # Хэшируем пароль перед сохранением
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            db.users.insert_one({
                'username': username,
                'password': hashed_password,
                'first_name': '',
                'last_name': '',
                'email': '',
                'phone': '',
                'gender': '',
                'city': ''
            })

            return redirect(url_for('auth'))

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']

    # Хэшируем пароль перед сохранением
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    db.users.insert_one({
        'username': username,
        'password': hashed_password,
        'first_name': '',
        'last_name': '',
        'email': '',
        'phone': '',
        'gender': '',
        'city': ''
    })

    return redirect(url_for('auth'))

@auth_ns.route('/logout')
class LogoutResource(Resource):
    @api.doc('logout_user')
    def post(self):
        """Logout a user"""
        session.pop('username', None)
        return redirect(url_for('auth'))

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)  # Удалите username из сессии
    return redirect(url_for('auth'))

@user_ns.route('/profile')
class ProfileResource(Resource):
    @api.doc('get_profile')
    def get(self):
        """Get user profile"""
        user = db.users.find_one({'username': session['username']})
        return render_template('profile.html', user=user)

    @api.doc('update_profile', body=user_model)
    def post(self):
        """Update user profile"""
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

@user_ns.route('/delete_profile')
class DeleteProfileResource(Resource):
    @api.doc('delete_profile')
    def post(self):
        """Delete user profile"""
        db.users.delete_one({'username': session['username']})
        session.clear()
        return redirect(url_for('index'))

@app.route('/delete_profile', methods=['POST'])
def delete_profile():
    db.users.delete_one({'username': session['username']})  # Удаление пользователя
    session.clear()  # Очистка сессии
    return redirect(url_for('index'))

@product_ns.route('/')
class ProductListResource(Resource):
    @api.doc('get_products')
    @api.param('category', 'Filter by category')
    @api.param('min_views', 'Filter by minimum views')
    @api.param('search', 'Search by product name')
    def get(self):
        """List all products with optional filters"""
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

@product_ns.route('/add')
class AddProductResource(Resource):
    @api.doc('get_add_product_form')
    def get(self):
        """Get add product form"""
        products = list(db.products.find())
        return render_template('add_product.html', products=products)

    @api.doc('add_product', body=product_model)
    def post(self):
        """Add a new product"""
        new_product = {
            'name': request.form['name'],
            'description': request.form['description'],
            'price': float(request.form['price']),
            'category': request.form['category'],
            'image_url': request.form['image_url'],
            'views': 0,
            'likes': 0
        }
        db.products.insert_one(new_product)
        return redirect(url_for('add_product'))

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        # Получаем данные из формы
        new_product = {
            'name': request.form['name'],
            'description': request.form['description'],
            'price': float(request.form['price']),
            'category': request.form['category'],
            'image_url': request.form['image_url'],
            'views': 0,
            'likes': 0
        }
        # Сохраняем продукт в базе данных
        db.products.insert_one(new_product)
        return redirect(url_for('add_product'))  # Перенаправляем на ту же страницу для добавления следующего продукта

    # Отображаем все продукты на странице добавления
    products = list(db.products.find())
    return render_template('add_product.html', products=products)

@product_ns.route('/<product_id>')
class ProductResource(Resource):
    @api.doc('get_product')
    def get(self, product_id):
        """Get a specific product by ID"""
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth'))

        product = db.products.find_one({"_id": ObjectId(product_id)})
        recommendations = get_user_recommendations(user_id)

        if product:
            # Record the view interaction in user_interactions collection
            db.user_interactions.insert_one({
                "user_id": user_id,
                "product_id": product_id,
                "interaction_type": "view"
            })

            # Update view count in the products collection for display purposes
            new_views_count = product.get('views', 0) + 1
            db.products.update_one(
                {"_id": ObjectId(product_id)},
                {"$set": {"views": new_views_count}}
            )
            product['views'] = new_views_count  # Update local view count for template display

            return render_template('product_detail.html', product=product, recommendations=recommendations)
        else:
            return "Product not found", 404

@app.route('/product/<product_id>')
def view_product(product_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth'))

    product = db.products.find_one({"_id": ObjectId(product_id)})
    recommendations = get_user_recommendations(user_id)

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

@product_ns.route('/edit/<product_id>')
class EditProductResource(Resource):
    @api.doc('get_edit_product_form')
    def get(self, product_id):
        """Get edit product form"""
        product = db.products.find_one({'_id': ObjectId(product_id)})
        return render_template('edit_product.html', product=product)

    @api.doc('edit_product', body=product_model)
    def post(self, product_id):
        """Edit a product"""
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
        return redirect(url_for('add_product'))

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

@product_ns.route('/delete/<product_id>')
class DeleteProductResource(Resource):
    @api.doc('delete_product')
    def post(self, product_id):
        """Delete a product"""
        db.products.delete_one({'_id': ObjectId(product_id)})
        return redirect(url_for('add_product'))

@app.route('/delete_product/<product_id>', methods=['POST'])
def delete_product(product_id):
    db.products.delete_one({'_id': ObjectId(product_id)})
    return redirect(url_for('add_product'))  # Возвращаемся к списку после удаления

@product_ns.route('/like/<product_id>')
class LikeProductResource(Resource):
    @api.doc('like_product')
    def post(self, product_id):
        """Like a product"""
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth'))

        # Record the like interaction in user_interactions collection
        db.user_interactions.insert_one({
            "user_id": user_id,
            "product_id": product_id,
            "interaction_type": "like"
        })

        # Update like count in the products collection for display purposes
        db.products.update_one(
            {"_id": ObjectId(product_id)},
            {"$inc": {"likes": 1}}  # Increment the like count
        )

        return redirect(url_for('view_product', product_id=product_id))

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

@cart_ns.route('/add/<product_id>')
class AddToCartResource(Resource):
    @api.doc('add_to_cart')
    def post(self, product_id):
        """Add a product to the cart"""
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

@cart_ns.route('/')
class CartResource(Resource):
    @api.doc('view_cart')
    def get(self):
        """View cart contents"""
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

@cart_ns.route('/remove/<product_id>')
class RemoveFromCartResource(Resource):
    @api.doc('remove_from_cart')
    def post(self, product_id):
        """Remove a product from the cart"""
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

@order_ns.route('/checkout/<user_id>')
class CheckoutResource(Resource):
    @api.doc('checkout')
    def post(self, user_id):
        """Process checkout and create an order"""
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

@order_ns.route('/<user_id>')
class OrdersResource(Resource):
    @api.doc('get_orders')
    def get(self, user_id):
        """Get all orders for a user"""
        orders = list(db.orders.find({'user_id': user_id}, {'_id': 0}))
        return render_template('orders.html', user_id=user_id, orders=orders)

@app.route('/orders/<user_id>', methods=['GET'])
def get_orders(user_id):
    orders = list(db.orders.find({'user_id': user_id}, {'_id': 0}))
    return render_template('orders.html', user_id=user_id, orders=orders)

@product_ns.route('/recommendations/<user_id>')
class RecommendationsResource(Resource):
    @api.doc('get_recommendations')
    def get(self, user_id):
        """Get product recommendations for a user"""
        user_cart = db.carts.find_one({'user_id': user_id})
        if user_cart:
            product_ids = user_cart.get('products', [])
            recommendations = list(db.products.find({'_id': {'$nin': product_ids}}, {'_id': 0}).limit(5))
            return render_template('recommendations.html', user_id=user_id, recommendations=recommendations)
        return render_template('recommendations.html', user_id=user_id, recommendations=[])

@app.route('/recommendations/<user_id>', methods=['GET'])
def recommendations_page(user_id):
    user_cart = db.carts.find_one({'user_id': user_id})
    if user_cart:
        product_ids = user_cart.get('products', [])
        recommendations = list(db.products.find({'_id': {'$nin': product_ids}}, {'_id': 0}).limit(5))
        return render_template('recommendations.html', user_id=user_id, recommendations=recommendations)
    return render_template('recommendations.html', user_id=user_id, recommendations=[])

# Helper functions
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

# Define backend for Swagger documentation - error handling
error_model = api.model('Error', {
    'message': fields.String(required=True, description='Error message')
})

# Register error handlers for common HTTP errors
@app.errorhandler(400)
def handle_bad_request(error):
    return jsonify({"message": "Bad request: " + str(error)}), 400

@app.errorhandler(401)
def handle_unauthorized(error):
    return jsonify({"message": "Unauthorized: " + str(error)}), 401

@app.errorhandler(404)
def handle_not_found(error):
    return jsonify({"message": "Resource not found: " + str(error)}), 404

@app.errorhandler(500)
def handle_server_error(error):
    return jsonify({"message": "Internal server error: " + str(error)}), 500

# Add global response documentation for all endpoints
@api.response(400, 'Bad Request', error_model)
@api.response(401, 'Unauthorized', error_model)
@api.response(404, 'Resource not found', error_model)
@api.response(500, 'Internal server error', error_model)
class GlobalResponseDocumentation:
    pass

if __name__ == '__main__':
    app.run(debug=True)