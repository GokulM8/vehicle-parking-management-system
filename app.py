from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    return "E-Commerce Project Started"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        print("REGISTER:", username, email, password)
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        print("LOGIN:", email, password)
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
