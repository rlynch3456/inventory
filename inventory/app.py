# inventory.py

import sqlite3
from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for
from flask_session import Session
from helpers import apology, get_date_string, usd, create_thumbnail, get_date_time_string, get_colors
import os
import csv
from io import StringIO
import logging
from icecream import ic

app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Let's create some logging
logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)
# For Info (we will use this to log user logins, logouts, and creations)
info_handler = logging.FileHandler('info.log')
info_handler.setLevel(logging.INFO)
info_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
info_handler.setFormatter(info_formatter)
logger.addHandler(info_handler)

@app.route('/download_csv')
def download_csv(data):


    # Create a CSV string
    csv_data = StringIO()
    csv_writer = csv.DictWriter(csv_data, fieldnames=['ItemID', 'Description', 'Category', 'Location', 'Brand', 'SerialNumber', 'Warranty', 'PurchaseDate',
                                                      'Value','Accessories', 'Notes'])
    csv_writer.writeheader()

    for row in data:
        row_dict = dict(row)

        fields = {'ItemID': row_dict['ItemID'], 'Description': row_dict['Description'], 'Category': row_dict['Category'], 'Location':row_dict['Location'],'Brand':row_dict['Brand'],
                    'SerialNumber': row_dict['SerialNumber'], 'Warranty': row_dict['Warranty'], 'PurchaseDate':row_dict['PurchaseDate'],
                    'Value': row_dict['Value'], 'Accessories':row_dict['Accessories'], 'Notes':row_dict['Notes']}

        csv_writer.writerow(fields)

    # Set up response headers
    response = Response(
        csv_data.getvalue(),
        mimetype='text/csv',
        content_type='application/octet-stream',
    )

    # create a unique filename for the csv
    name = get_date_time_string()
    # Set the file name for the download
    response.headers['Content-Disposition'] = f'attachment; filename=data_{name}.csv'

    return response

def get_item_details(itemID):

    command = (
        "SELECT * from ItemDetails "
        "JOIN LocationList on ItemDetails.LocationID = LocationList.LocationID "
        "JOIN CategoryList on ItemDetails.CategoryID = CategoryList.CategoryID "
        "Join BrandList on ItemDetails.BrandID = BrandList.BrandID "
        f"Where ItemID= {itemID}"
    )

    db = get_db()
    cursor = db.execute(command)

    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    db.close()

    row_dict = dict(zip(columns, row))

    return row_dict

def get_items_by_group(grouping):

    data = []
    if grouping == 'location':
        groups = get_location_list()
    elif grouping == 'category':
        groups = get_category_list()
    else:
        groups = get_brand_list()
    
    db = get_db()
    cursor = db.cursor()

    for group in groups:
        group_id = group[0]
        if grouping == 'location':
            cursor.execute('SELECT ItemID FROM ItemDetails WHERE LocationID = ?', (group_id,))
            session['grouping'] = 'location'
        elif grouping == 'category':
            cursor.execute('SELECT ItemID FROM ItemDetails WHERE CategoryID = ?', (group_id,))
            session['grouping'] = 'category'
        else:
            cursor.execute('SELECT ItemID FROM ItemDetails WHERE BrandID = ?', (group_id,))
            session['grouping'] = 'brand'



        items = cursor.fetchall()
        if(len(items) != 0):
            if grouping == 'location':
                data.append({'group': group['Location'], 'itemlist': [get_item_details(item['ItemID']) for item in items]})
            elif grouping == 'category':
                data.append({'group': group['Category'], 'itemlist': [get_item_details(item['ItemID']) for item in items]})
            else:
                data.append({'group': group['Brand'], 'itemlist': [get_item_details(item['ItemID']) for item in items]})
    db.close()
    return data

def get_item_images(itemID):

    db = get_db()
    command = f"SELECT *FROM ImageList WHERE ItemID = {itemID}"
    cursor = db.execute(command)
    rows = cursor.fetchall()
    db.close()

    return rows

def get_db():
    file_name = 'inventory_' + str(session['userID']) + '.db'
    db = sqlite3.connect(file_name, check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db

def create_db(UserID):

    # This will create an empty database with default Location, Category, and Brand

    file_name = 'inventory_' + str(UserID) + '.db'
    db = sqlite3.connect(file_name, check_same_thread=False)
    db.row_factory = sqlite3.Row

    try:
        with open('inventory.db.sql', 'r') as sql_file:
            sql_script = sql_file.read()
            cursor = db.cursor()
            cursor.executescript(sql_script)
            db.commit()
            db.close()
    except Exception as e:
        return False
    

def get_category_list():

    db = get_db()
    command = "SELECT CategoryID, Category FROM CategoryList ORDER BY Category"
    key='Category'
    cursor = db.execute(command)
    rows = cursor.fetchall()
    db.close()

    return rows
    
def get_location_list():

    db = get_db()
    command = "SELECT * FROM LocationList ORDER BY Location"
    key='Location'
    cursor = db.execute(command)
    rows = cursor.fetchall()
    db.close()
    return rows

def get_brand_list():

    db = get_db()
    command = "SELECT * FROM BrandList ORDER BY Brand"
    key='Brand'
    cursor = db.execute(command)
    rows = cursor.fetchall()
    db.close()
    return rows

'''
This function can be used generically to delete an item from a list, such as
CategoryList, LocationList, etc.

One of the things it will do is to reasign as needed.  For example if a category is removed,
any ItemDetail that references this category will be reasigned to the detault.
'''
def delete_list_item(table, item_id):
    success = False

    db = get_db()

    # let's search for any records that reference this id
    command = ("SELECT * FROM ItemDetails "
               f"JOIN {table}List on ItemDetails.{table}ID = {table}List.{table}ID "
               f"WHERE ItemDetails.{table}ID = {item_id}")
    cursor = db.execute(command)
    
    rows = cursor.fetchall()

    command = (
        f"UPDATE ItemDetails "
        f"SET {table}ID = '1' "
        f"WHERE {table}ID = {item_id}"
    )
    cursor = db.execute(command)
    row_count = cursor.rowcount

    command = (
        f"DELETE FROM {table}List "
        f"WHERE {table}ID = {item_id}"
    )
    cursor = db.execute(command)

    db.commit()
    db.close()
    return row_count

def rename_list_item(table, item_id, name, column):

    db = get_db()
    data_to_update = (table, column, name, column, item_id)
    command = (f"UPDATE {table} SET {column}='{name}' WHERE {column}ID = {item_id}")

    cursor = db.cursor()
    cursor.execute(command)
    db.commit()
    cursor.close()
    db.close()

    return f"{column}ID updated to {name}"

@app.route("/inventory_old")
def inventory_old():

    # as a start, let's list everything in the inventory

    # TODO: allow different inventories such as by location, category, etc.

    # we will want to see: Description, location, category and brand

    db = get_db()

    command = (
        "SELECT Description, Location FROM ItemDetails "
        "JOIN LocationList on ItemDetails.LocationID = LocationList.LocationID "
    )

    cursor = db.execute(command)
    rows = cursor.fetchall()
    db.close()

    return render_template("inventory.html", rows=rows)


@app.route("/inventory", methods = ['POST', 'GET'])
def inventory():

    locations = get_location_list()
    categories = get_category_list()
    brands = get_brand_list()

    where_clause = f"AND ItemDetails.CategoryID != 0 "
    location = category = brand = 0

    if request.method == "POST":

        # we want to filter based on the selection(s) of location, category, and/or brand

        if request.method == 'POST':
            category = request.form.get('category')
        if category != '0':
            where_clause = where_clause + f" AND ItemDetails.CategoryID = {category} "
        location = request.form.get('location')
        if location != '0':
            where_clause = where_clause + f" AND ItemDetails.LocationID = {location} "
        brand = request.form.get('brand')
        if brand != '0':
            where_clause = where_clause + f" AND ItemDetails.BrandID = {brand}"





        db = get_db()

        command = ("SELECT ItemID, Description, Brand, Location, Category FROM ItemDetails "
                    "JOIN BrandList ON ItemDetails.BrandID = BrandList.BrandID "
                    "JOIN CategoryList ON ItemDetails.CategoryID = CategoryList.CategoryID "
                    "JOIN LocationList ON ItemDetails.LocationID = LocationList.LocationID "
                    f"{where_clause} "
        )
        cursor = db.execute(command)
        rows = cursor.fetchall()
        db.close()

        return render_template("inventory.html", rows=rows, locations=locations, categories=categories, brands=brands, location_selection=int(location), category_selection=int(category), brand_selection=int(brand))


    else:
        db = get_db()

        command = ("SELECT ItemID, Description, Brand, Location, Category FROM ItemDetails "
                    "JOIN BrandList ON ItemDetails.BrandID = BrandList.BrandID "
                    "JOIN CategoryList ON ItemDetails.CategoryID = CategoryList.CategoryID "
                    "JOIN LocationList ON ItemDetails.LocationID = LocationList.LocationID "
        )
        cursor = db.execute(command)
        rows = cursor.fetchall()
        db.close()

        return render_template("inventory.html", rows=rows, locations=locations, categories=categories, brands=brands, location_selection=int(location), category_selection=int(category), brand_selection=int(brand))


@app.route("/search", methods=['GET', 'POST'])
def search():

    locations = get_location_list()
    categories = get_category_list()
    brands = get_brand_list()
    if request.method == 'POST':
        search_raw =  request.form.get("search")
    else:    
        search_raw =  request.args.get("search")

    # Fix any apostrophes 
    search = search_raw.replace("'", "''")

    db = get_db()

    command = ("SELECT ItemID, Description, Brand, Location, Category from ItemDetails "
               "JOIN BrandList ON ItemDetails.BrandID = BrandList.BrandID "
               "JOIN CategoryList ON ItemDetails.CategoryID = CategoryList.CategoryID "
               "JOIN LocationList ON ItemDetails.LocationID = LocationList.LocationID "
               f"where Description like '%{search}%'"
               f" OR Notes like '%{search}%'"
               f" OR Accessories like '%{search}%'"
               f" OR Brand like '%{search}%' "
    )
    
    cursor = db.execute(command)
    rows = cursor.fetchall()
    db.close()

    return render_template("inventory.html", message="Hello World, how fitting!", rows=rows, search=search, locations=locations, categories=categories, brands=brands)

@app.route("/row_click")
def row_click():
    print("got to row click")

@app.route('/category_add', methods=['POST'])
def category_add():
    category = request.form.get('new_name')

    db = get_db()

    command = "INSERT INTO CategoryList ('Category') VALUES (?)"

    cursor = db.cursor()
    cursor.execute(command, (category,))
    db.commit()
    db.close()

    rows = get_category_list()
    return render_template("category.html", rows=rows, list='category', listName='Categories')
    return category + " added!"

@app.route('/brand_add', methods=['POST'])
def brand_add():
    brand = request.form.get('new_name')

    db = get_db()

    command = "INSERT INTO BrandList ('Brand') VALUES (?)"

    cursor = db.cursor()
    cursor.execute(command, (brand,))
    db.commit()
    db.close()

    rows = get_brand_list()
    return render_template("brand.html", rows=rows)
    return category + " added!"

@app.route('/location_add', methods=['POST'])
def location_add():
    location = request.form.get('new_name')

    db = get_db()

    command = "INSERT INTO LocationList ('Location') VALUES (?)"

    cursor = db.cursor()
    cursor.execute(command, (location,))
    db.commit()
    db.close()

    rows = get_location_list()
    return render_template("location.html", rows=rows)
    return category + " added!"

@app.route('/category', methods=['GET', 'POST'])
def category():
            
    rows = get_category_list()

    if request.method == "POST":

        action_value = request.form.get('action')
        action, item_id = action_value.split('_')

        if action == 'rename':
            name = request.form.get(item_id)
            rename_list_item('CategoryList', item_id, name, 'Category')
        if action == 'delete':
            deletedName = request.form.get(f"nameHidden{item_id}")
            row_count = delete_list_item('Category', item_id)
            return render_template("apology.html", message=f"{row_count} items had the category changed to {rows[0]['Category']} when {deletedName} was deleted.")

        # something changes, so need to reload the rows
        rows = get_category_list()
        return render_template("category.html", rows=rows, list='category', listName='Categories')
    else:
        return render_template("category.html", rows=rows, list='category', listName='Categories')

@app.route('/brand', methods=['GET', 'POST'])
def brand():
            
    rows = get_brand_list()
    if request.method == "POST":

        action_value = request.form.get('action')
        action, item_id = action_value.split('_')

        if action == 'rename':
            name = request.form.get(item_id)
            rename_list_item('BrandList', item_id, name, 'Brand')
        if action == 'delete':
            row_count = delete_list_item('Brand', item_id)
            deletedName = request.form.get(f"nameHidden{item_id}")
            return render_template("apology.html", message=f"{row_count} items had the Brand changed to {rows[0]['Brand']} when {deletedName} was deleted.")


        # something changes, so need to reload the rows
        rows = get_brand_list()
        return render_template("brand.html", rows=rows)
    else:
        return render_template("brand.html", rows=rows)

@app.route('/location', methods=['GET', 'POST'])
def location():
            
    rows = get_location_list()
    if request.method == "POST":

        action_value = request.form.get('action')
        action, item_id = action_value.split('_')

        if action == 'rename':
            name = request.form.get(item_id)
            rename_list_item('LocationList', item_id, name, 'Location')
        if action == 'delete':
            row_count = delete_list_item('Location', item_id)
            deletedName = request.form.get(f"nameHidden{item_id}")
            return render_template("apology.html", message=f"{row_count} items had the location changed to {rows[0]['Location']} when {deletedName} was deleted.")


        # something changes, so need to reload the rows
        rows = get_location_list()
        return render_template("location.html", rows=rows)
    else:
        return render_template("location.html", rows=rows)


@app.route("/", methods=["GET", "POST"])
def index():

    # Let's get some stats for the homepage
    db = get_db()

    command = (
        'select LocationList.Location, count(ItemDetails.LocationID)  from ItemDetails '
        'join LocationList on ItemDetails.LocationID=LocationList.LocationID '
        'group by ItemDetails.LocationID  order by LocationList.Location'
    )

    cursor = db.execute(command)
    locations = cursor.fetchall()

    command = (
        'SELECT CategoryList.Category, count(ItemDetails.CategoryID) FROM ItemDetails '
        'JOIN CategoryList on ItemDetails.CategoryID = CategoryList.CategoryID '
        'GROUP BY ItemDetails.CategoryID ORDER BY CategoryList.Category'
    )

    cursor = db.execute(command)
    categories = cursor.fetchall()

    db.close()

    return render_template("index.html", locations=locations, categories=categories)

@app.route("/delete_item/<int:itemID>", methods = ["POST"])
def delete_item(itemID):

    db = get_db()
    db.execute("DELETE FROM ItemDetails WHERE ItemID=?", (itemID,))
    db.commit()

    # Let's see if there are any images associated with this item.
    images = get_item_images(itemID)

    for image in images:
        try:
            os.remove(f"static/images/{image['FileName']}")
        except OSError as e:
            print(f'Error: {e.filename} - {e.strerror}')

    for image in images:
        try:
            os.remove(f"static/images/{image['ThumbnailName']}")
        except OSError as e:
            print(f'Error: {e.filename} - {e.strerror}')

    # now delete from the database
    command = f"DELETE from ImageList WHERE ItemID = {itemID}"
    db.commit()
    cursor = db.execute(command)
    print(f'{cursor.rowcount} images deleted')

    db.close()

    result = redirect(url_for('index'))

    return result


@app.route("/delete_confirm/<int:itemID>", methods=["POST"])
def delete_confirm(itemID):

    db = get_db()
    cursor = db.execute("SELECT * FROM ItemDetails WHERE ItemID=?", (itemID,))
    row_to_delete = cursor.fetchone()
    cursor.close()
    db.close()

    return render_template('delete_confirm.html', row = row_to_delete)
    

@app.route("/update_item", methods=["POST", "GET"])
def update_item():

# Retrieve data to update from your request or other sources
    itemID = request.form.get('ItemIDHidden')
    description = request.form.get('description')
    notes = request.form.get('notes')
    # We need to assign the default category, location, and brand if user did not select anything
    category = str(request.form.get('category'))

    # If the user did not select a category from the dropdown, we will not be able to convert to an int
    try:
        int(category)
    except:
        category = '1'
    location = str(request.form.get('location'))
    try:
        int(location)
    except:
        location = '1'
    brand = str(request.form.get('brand'))
    try:
        int(brand)
    except:
        brand = '1'

    serialNumber = request.form.get('serialNumber')
    accessories = request.form.get('accessories')
    purchase_date = request.form.get('purchase_date')
    today = get_date_string()
    value = request.form.get('worth')
    warranty = request.form.get('warranty')

    if request.method == 'POST':

        db = get_db()
        data_to_update = (description, notes, category, location, brand, serialNumber, accessories, purchase_date, today, today, value, warranty, itemID)
        command = (
            "UPDATE ItemDetails SET Description=?, Notes=?, CategoryID=?, LocationID=?, BrandID=?, serialNumber=?, Accessories=?, PurchaseDate=?, CreatedDate=?, ModifiedDate=?, Value=?, Warranty=? "
            "WHERE ItemID=?"
        )
        cursor = db.cursor()
        cursor.execute(command, data_to_update)
        db.commit()
        cursor.close()
        db.close()

    return redirect(url_for('item_details', item_id=itemID))


# Add a new item
@app.route("/add_item", methods=["GET", "POST"])
def add_item():
    
    if request.method == "POST":
        # get the new item details and add a new record

        description = request.form.get('description')
        notes = request.form.get('notes')
        # We need to assign the default category, location, and brand if user did not select anything
        category = str(request.form.get('category'))
        try:
            int(category)
        except:
            category = '1'
        location = str(request.form.get('location'))
        try:
            int(location)
        except:
            location = '1'
        brand = str(request.form.get('brand'))
        try:
            int(brand)
        except:
            brand = '1'
        serialNumber = request.form.get('serialNumber')
        accessories = request.form.get('accessories')
        purchase_date = request.form.get('purchase_date')
        value = request.form.get('worth')
        warranty = request.form.get('warranty')
        today = get_date_string()

        db = get_db()
        data_to_insert = (description, notes, category, location, brand, serialNumber, accessories, today, today, value, warranty, purchase_date)
        command = ("INSERT INTO ItemDetails (Description, Notes, CategoryID, LocationID, BrandID, serialNumber, Accessories, CreatedDate, ModifiedDate, Value, Warranty, PurchaseDate)"
                   "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
        )
        cursor = db.cursor()
        cursor.execute(command, data_to_insert)
        db.commit()

        # now let's get the item number of the row that we just added
        command = 'SELECT ItemID FROM ItemDetails ORDER BY ItemID DESC LIMIT 1'
        cursor=db.execute(command)
        row = cursor.fetchone()
        db.close()
        return redirect(url_for('item_details',item_id=row[0]))

    else:
        # fill out a new item with some default values

        categories = get_category_list()
        brands = get_brand_list()
        locations = get_location_list()

        # set the default purchase date to today
        purchase_date = get_date_string()  

        return render_template("item_details.html", itemID=0, item=None, categories=categories,locations=locations, brands=brands, categoryID=0, locationID=0, brandID=0)

@app.route('/export/<string:type>')
def export(type):

    grouping = session['grouping']

    if grouping == 'category':
        order = 'Category'
    elif grouping == 'location':
        order = 'Location'
    else:
        order = 'Brand'
    
    command = (
    "SELECT * from ItemDetails "
    "JOIN LocationList on ItemDetails.LocationID = LocationList.LocationID "
    "JOIN CategoryList on ItemDetails.CategoryID = CategoryList.CategoryID "
    "Join BrandList on ItemDetails.BrandID = BrandList.BrandID "
    f"ORDER BY {order}"
    )



    db = get_db()
    cursor = db.execute(command)
    rows = cursor.fetchall()
    db.close()

    return download_csv(rows)

@app.route('/report/<string:group>')
def repport_specific(group):
    data = get_items_by_group(group)
    return render_template('report.html', data=data, group=group)

@app.route('/report')
def report():
    data = get_items_by_group('location')
    return render_template('report.html', data=data, group='location')

@app.route("/item_details", methods=["GET", "POST"])
def item_details():


    if request.method == "POST":
        return render_template("apology.html", message="Not so fast...")
    else:
        item_id = request.args.get("item_id")

        item_row= get_item_details(item_id)
        item_dict = dict(item_row)

        image_path = dir = os.path.join(os.getcwd(), 'images')

        categories = get_category_list()
        brands = get_brand_list()
        locations = get_location_list()
        images = get_item_images(item_id)
        serialized_images = [dict(image) for image in images]

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # If it's an AJAX request, return JSON
            return jsonify(item=item_dict, categories=dict(categories), locations=dict(locations), brands=dict(brands), categoryID=item_dict['CategoryID'], locationID=item_dict['LocationID'], brandID=item_dict['BrandID'], image_path=image_path, images=serialized_images)
        else:
            return render_template("item_details.html", itemID=item_dict['ItemID'], item=item_dict, categories=categories,locations=locations, brands=brands, categoryID=item_dict['CategoryID'], locationID=item_dict['LocationID'], brandID=item_dict['BrandID'], image_path=image_path, images=images)

@app.route('/image_delete', methods=['POST'])
def image_delete():

    imageID = request.form.get('action')
    itemID = request.form.get('itemID')

    db = get_db()

    command = (
        "SELECT * FROM ImageList "
        f"WHERE ID = {imageID}"
    )
    cursor = db.execute(command)
    image_list = cursor.fetchall()

    # now delete the image and thumbnail if there is one
    image_folder = 'static/images/'
    for image in image_list:
        path = image_folder + image['FileName']
        os.remove(path)
        path = image_folder + image['ThumbnailName']
        os.remove(path)

    command = (
        "DELETE FROM ImageList "
        f"WHERE ID = {imageID}"
    )
    cursor = db.execute(command)
    db.commit()
    db.close()

    return images(itemID)


@app.route('/images/<int:itemID>', methods=['GET', 'POST'])
def images(itemID):
    item_details = get_item_details(itemID)
    images = get_item_images(itemID)
    return render_template('images.html', itemID=itemID, images=images, description=item_details['Description'])

@app.route('/upload', methods=['POST'])
def upload():

    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'

        file = request.files['file']

        if file.filename == '':
            return 'No selected file'

        itemID = request.form.get('itemID')
        # Save the uploaded file to a folder (or process it as needed)
        image_path = 'static/images/' + file.filename
        file.save(image_path)
        

        # make a thumbnail if appropriate
        thumb_name = create_thumbnail(image_path, 'static/images/', 250, 250)
        itemID = request.form.get('itemID')

        # Let's add to the database
        db = get_db()

        data_to_insert = (file.filename, thumb_name, itemID)
        command = ("INSERT INTO ImageList (FileName, ThumbnailName, ItemID) "
                "VALUES (?,?,?)"
                )
        cursor = db.cursor()
        cursor.execute(command, data_to_insert)
        db.commit()
        db.close()
        return images(itemID)

@app.route('/users', methods=['GET', 'POST'])
def users():

    # get the users database
    db = sqlite3.connect("users.db", check_same_thread=False)
    db.row_factory = sqlite3.Row

    # check to see if this name is already taken
    command = f"SELECT * FROM Users"

    cursor = db.execute(command)

    rows = cursor.fetchall()

    if request.method == 'POST':

        return render_template('users.html', users=rows)

    else:
        return render_template('users.html', users=rows)

@app.route('/login', methods=['GET', 'POST'])
def login():

    session.clear()
    if request.method == 'POST':
        # get the username
        username = request.form.get('username')

        # see if the user is registered

        # get the users database
        db = sqlite3.connect("users.db", check_same_thread=False)
        db.row_factory = sqlite3.Row

        cursor = db.execute('SELECT * FROM Users WHERE Username=?', (username,))
        rows = cursor.fetchall()

        # Is this user registered?
        if len(rows) == 0:
            return render_template('apology.html', message=f'{username} is a not registered user')
        else:
            session['userID'] = rows[0]['ID']
            session['username'] = username
            if rows[0]['isAdmin'] == 1:
                session['userRole'] = 'admin'
            logger.info(f'User: {session["username"]}: UserID: {session["userID"]} logged in.')

        return redirect('/')
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    logger.info(f'User: {session["username"]}: UserID: {session["userID"]} logged out.')
    session.clear()
    return redirect('/')

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':
        username = request.form.get('username')

        # get the users database
        db = sqlite3.connect("users.db", check_same_thread=False)
        db.row_factory = sqlite3.Row

        # check to see if this name is already taken
        command = f"SELECT * FROM Users WHERE Username ='?'"

        cursor = db.execute('SELECT * FROM Users WHERE Username=?', (username,))

        rows = cursor.fetchall()

        if len(rows) != 0:
            return render_template('apology.html', message=f'Sorry, but the username {username} has already been used')
        else:
            # looks good, create a new user
            command = f'INSERT INTO Users (Username) VALUES(?)'
            cursor.execute(command, (username,))
            db.commit()

            # now get the UserID of the new user
            command = 'SELECT * FROM Users ORDER BY ID DESC LIMIT 1'
            cursor.execute(command)
            row = cursor.fetchone()
            UserID = row['ID']
            db.close()

            create_db(UserID)
            session['UserName'] = username
            logger.info(f'User: {username} created with ID: {UserID}')
            return render_template('login.html', message=f"{username}, you have registered, please log in")
    else:
        return render_template('register.html')



