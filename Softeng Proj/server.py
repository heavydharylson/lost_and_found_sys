from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory,
    render_template,
    redirect,
    url_for,
    session,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)

from flask_cors import CORS
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from skimage import img_as_float
import numpy as np
import os
from werkzeug.utils import secure_filename
import shutil
import re


# 1. Initialize Flask app
app = Flask(__name__)

# 2. Set up application configurations
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"  # Database URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # Turn off track modifications
app.config["SECRET_KEY"] = "secret_key"  # Flask's session management key

# 3. Initialize extensions
CORS(app, supports_credentials=True)
db = SQLAlchemy(app)  # Database object

# 4. Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# 5. Configure login view for Flask-Login
login_manager.login_view = (
    "login"  # Redirect to the login page if the user is not authenticated
)


# Set up absolute paths for directories
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
GADGET_FOLDER = os.path.join(BASE_DIR, "Inventory", "gadget")
ACCESSORY_FOLDER = os.path.join(BASE_DIR, "Inventory", "accessory")
USER_DATA_DIR = os.path.join(BASE_DIR, "user_data")

# Ensure directories exist
os.makedirs(GADGET_FOLDER, exist_ok=True)
os.makedirs(ACCESSORY_FOLDER, exist_ok=True)
os.makedirs(USER_DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    contact_no = db.Column(db.String(11), nullable=False)

    def __repr__(self):
        return f"<User {self.email}>"

    def is_authenticated(self):
        return True  # User is always considered authenticated once logged in

    def get_id(self):
        return str(self.id)  # Flask-Login requires the ID to be a string

    def is_active(self):
        return True  # Assuming all users are active by default, you can customize this if needed


# Assuming you are using SQLAlchemy for database interaction
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    user = db.relationship("User", backref="items")  # Relation to the User model

    def __repr__(self):
        return f"<Item {self.title}>"


with app.app_context():
    db.create_all()  # Creates the 'users' table


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Retrieve user by ID


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/logout")
def logout():
    logout_user()  # Properly log the user out
    print("User logged out.")
    return redirect(url_for("login"))


@app.route("/static/images/<category>/<filename>")
def serve_image(category, filename):
    folder = GADGET_FOLDER if category == "gadget" else ACCESSORY_FOLDER
    return send_from_directory(folder, filename)


def validate_contact_number(contact_no):
    # Check if the contact number is 11 digits long and starts with '09'
    if re.match(r"^09\d{9}$", contact_no):
        return True
    return False


# Helper function to save user data
def save_user(email, password, full_name, contact_no):
    # Create a new user and add it to the database
    user = User(
        email=email,
        password=password,
        full_name=full_name,
        contact_no=contact_no,
    )
    db.session.add(user)  # Add the user to the session
    db.session.commit()  # Commit the changes to the database


# Helper function to retrieve user data
def get_user_data(email):
    user = User.query.filter_by(email=email).first()
    if user:
        print(f"User found: {user.email}")
    else:
        print("No user found.")
    return user


allowed_domains = [
    "cvsu.edu.ph",
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "msn.com",
    "icloud.com",
    "yandex.com",
]


@app.route("/login", methods=["POST", "GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = get_user_data(email)

        if user and user.password == password:
            login_user(user)
            print("Login successful!")
            return redirect(url_for("dashboard"))

        # Modify the response to return an HTML error message
        error_message = "Invalid credentials"
        return render_template("login.html", error=error_message)

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json()  # Get JSON data from the request body
        email = data.get("email")
        password = data.get("password")
        full_name = data.get("full_name")
        contact_no = data.get("contact_no")

        # Check if email, password, full name, and contact number are provided
        if not email or not password or not full_name or not contact_no:
            return (
                jsonify({"success": False, "message": "All fields are required"}),
                400,
            )

        # Validate email domain
        if not email.endswith(tuple(f"@{domain}" for domain in allowed_domains)):
            return (
                jsonify(
                    {"success": False, "message": "Please use a valid email address."}
                ),
                400,
            )

        # Validate contact number
        if not validate_contact_number(contact_no):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Contact number must be 11 digits and start with '09'.",
                    }
                ),
                400,
            )

        # Check if user already exists
        existing_user = get_user_data(email)
        if existing_user:
            return (
                jsonify({"success": False, "message": "User already registered"}),
                400,
            )

        # Save the user data to the database
        save_user(email, password, full_name, contact_no)
        return (
            jsonify(
                {"success": True, "message": "Registration successful. Please log in."}
            ),
            200,
        )

    return render_template("register.html")


@app.route("/dashboard")
@login_required
def dashboard():
    print("Redirecting to dashboard...")
    return render_template("content.html", user=current_user)


@app.route("/profile")
@login_required
def profile():
    # Fetch the current user's information
    user_data = {
        "email": current_user.email,
        "full_name": current_user.full_name,  # Ensure 'full_name' exists in your User model
        "contact_no": current_user.contact_no,  # Ensure 'contact_no' exists in your User model
    }

    # Fetch items posted by the current user
    user_items = Item.query.filter_by(user_id=current_user.id).all()

    return render_template("profile.html", user=user_data, items=user_items)


@app.route("/profile/<int:user_id>")
def user_profile(user_id):
    # Get the user by their ID
    user = User.query.get(user_id)

    if user is None:
        return redirect(url_for("dashboard"))

    # Fetch items posted by the user
    user_items = Item.query.filter_by(user_id=user.id).all()

    return render_template("profile.html", user=user, items=user_items)


@app.route("/list-items")
@login_required
def list_items():
    # Query all items from the database
    items = Item.query.all()

    # Prepare the list of items with their associated user names
    items_data = []
    for item in items:
        user = User.query.get(item.user_id)

        # Determine the folder based on the category
        if item.category == "gadget":
            folder = "gadget"
        elif item.category == "accessory":
            folder = "accessory"
        else:
            folder = ""  # Default or other category handling

        # Construct the image file path
        image_path = f"/static/images/{folder}/{item.filename}"

        items_data.append(
            {
                "title": item.title,
                "description": item.description,
                "filename": image_path,  # Include the full path
                "user_name": user.full_name,  # Fetch the name of the user who uploaded the item
                "user_id": user.id,  # Add user_id to the response
            }
        )

    # Return the items as JSON
    return jsonify(items_data)


@app.route("/upload", methods=["POST"])
@login_required
def upload_file():
    category = request.form.get("category")
    title = request.form.get("title")
    description = request.form.get("description")
    file = request.files.get("file")

    if not category or not title or not description or not file:
        return jsonify({"success": False, "message": "All fields are required"}), 400

    # Validate category
    if category not in ["gadget", "accessory"]:
        return jsonify({"success": False, "message": "Invalid category"}), 400

    try:
        if current_user.is_authenticated:
            # Secure the filename
            filename = secure_filename(file.filename)

            # Save the file to the appropriate folder based on category
            target_folder = GADGET_FOLDER if category == "gadget" else ACCESSORY_FOLDER
            file_path = os.path.join(target_folder, filename)
            file.save(file_path)

            # Save file details to the database
            item = Item(
                title=title,
                description=description,
                category=category,
                filename=filename,
                user_id=current_user.id,  # Associate the file with the logged-in user
            )
            db.session.add(item)
            db.session.commit()

            return jsonify({"success": True, "message": "Item uploaded successfully"})
        else:
            return (
                jsonify({"success": False, "message": "User is not authenticated"}),
                401,
            )
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# Resize image to fit within a target size while maintaining aspect ratio
def resize_image_with_padding(image, target_size):
    image.thumbnail(target_size, Image.LANCZOS)
    new_image = Image.new("RGB", target_size, (255, 255, 255))
    new_image.paste(
        image,
        ((target_size[0] - image.size[0]) // 2, (target_size[1] - image.size[1]) // 2),
    )
    return new_image


# Compare two images and return similarity score
def compare_images(image1, image2):
    image1 = img_as_float(np.array(image1))
    image2 = img_as_float(np.array(image2))

    image1_gray = np.dot(image1[..., :3], [0.2989, 0.5870, 0.1140])
    image2_gray = np.dot(image2[..., :3], [0.2989, 0.5870, 0.1140])

    similarity_index, _ = ssim(image1_gray, image2_gray, full=True, data_range=1)
    return round(similarity_index * 100, 2)  # Round to 2 decimal places


# Compare uploaded image with inventory images in a category
def find_similar_images(uploaded_image_path, category_folder, category):
    matches = []
    uploaded_image = Image.open(uploaded_image_path)

    for inventory_image_name in os.listdir(category_folder):
        inventory_image_path = os.path.join(category_folder, inventory_image_name)
        inventory_image = Image.open(inventory_image_path)

        target_size = (
            min(uploaded_image.size[0], inventory_image.size[0]),
            min(uploaded_image.size[1], inventory_image.size[1]),
        )
        resized_uploaded_image = resize_image_with_padding(uploaded_image, target_size)
        resized_inventory_image = resize_image_with_padding(
            inventory_image, target_size
        )

        similarity = compare_images(resized_uploaded_image, resized_inventory_image)
        if similarity >= 50:  # Only consider matches above 50%
            matches.append(
                {
                    "filename": inventory_image_name,
                    "similarity": round(similarity, 2),
                    "url": f"/static/images/{category}/{inventory_image_name}",  # Use category here
                }
            )

    matches.sort(key=lambda x: x["similarity"], reverse=True)
    return matches


@app.route("/compare", methods=["POST"])
def compare_uploaded_image():
    if "file" not in request.files or "category" not in request.form:
        return (
            jsonify({"success": False, "message": "File and category are required"}),
            400,
        )

    file = request.files["file"]
    category = request.form.get("category")  # Retrieve category here

    if file.filename == "":
        return jsonify({"success": False, "message": "No selected file"}), 400

    uploaded_image_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(uploaded_image_path)

    # Determine the folder to search based on the selected category
    search_folder = (
        GADGET_FOLDER
        if category == "gadget"
        else ACCESSORY_FOLDER if category == "accessory" else None
    )

    if not search_folder:
        return jsonify({"success": False, "message": "Invalid category"}), 400

    # Pass the category to the find_similar_images function
    matches = find_similar_images(uploaded_image_path, search_folder, category)

    if matches:
        # Add user_id to the match data
        for match in matches:
            # Get the item that matches the uploaded image
            inventory_item = Item.query.filter_by(filename=match["filename"]).first()

            if inventory_item:
                match["user_id"] = inventory_item.user_id  # Add user_id from the item

        return jsonify({"success": True, "matches": matches})
    else:
        return jsonify({"success": False, "message": "No matches found"})


if __name__ == "__main__":
    app.run(debug=True)
