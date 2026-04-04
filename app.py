from flask import Flask, render_template, request, redirect
import boto3
from datetime import datetime
from dotenv import load_dotenv
import os

app = Flask(__name__)

# ✅ LOAD ENV
load_dotenv()

print(os.getenv("AWS_REGION"))
# ✅ AWS CONFIG FROM .env
dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.getenv("AWS_REGION"),
    #region_name='ap-south-1',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY")
)

table = dynamodb.Table('visitors')

s3 = boto3.client(
    's3',
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY")
)

BUCKET_NAME = os.getenv("BUCKET_NAME")


# 🏠 Home Page
@app.route('/')
def index():
    return render_template('index.html')


# ➕ Add Visitor
@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    phone = request.form['phone']
    branch = request.form['branch']
    year = request.form['year']
    purpose = request.form['purpose']

    file = request.files.get('photo')

    if file and file.filename != "":
        file_name = file.filename
        s3.upload_fileobj(file, BUCKET_NAME, file_name)
        file_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_name}"
    else:
        file_url = ""

    table.put_item(
        Item={
            "id": phone,
            "name": name,
            "phone": phone,
            "branch": branch,
            "year": year,
            "purpose": purpose,
            "photo": file_url,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    )

    return redirect('/')


# 📋 View Records
@app.route('/admin')
def admin():
    response = table.scan()
    visitors = response.get('Items', [])
    return render_template('admin.html', visitors=visitors)


# 🗑️ Delete Record
@app.route('/delete/<id>')
def delete(id):
    table.delete_item(Key={"id": id})
    return redirect('/admin')


# ✏️ Edit Record
@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    if request.method == 'POST':
        table.update_item(
            Key={"id": id},
            UpdateExpression="set #n=:n, phone=:p, branch=:b, #y=:y, purpose=:pr",
            ExpressionAttributeNames={
                "#n": "name",
                "#y": "year"
            },
            ExpressionAttributeValues={
                ":n": request.form['name'],
                ":p": request.form['phone'],
                ":b": request.form['branch'],
                ":y": request.form['year'],
                ":pr": request.form['purpose']
            }
        )
        return redirect('/admin')

    response = table.get_item(Key={"id": id})
    data = response.get('Item', {})
    return render_template('edit.html', data=data)


# 📊 Dashboard
@app.route('/dashboard')
def dashboard():
    response = table.scan()
    visitors = response.get('Items', [])

    total = len(visitors)

    branch_count = {}
    for v in visitors:
        branch = v.get("branch", "Unknown")
        branch_count[branch] = branch_count.get(branch, 0) + 1

    return render_template(
        'dashboard.html',
        total=total,
        branch_count=branch_count
    )


# 🚀 Run App
if __name__ == '__main__':
    app.run(debug=True)