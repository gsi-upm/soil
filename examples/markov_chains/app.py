from flask import Flask
import solara.server.flask

app = Flask(__name__)
app.register_blueprint(solara.server.flask.blueprint, url_prefix="/solara/")


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

