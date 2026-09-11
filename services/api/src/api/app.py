from asgiref.wsgi import WsgiToAsgi
from flask import Flask
from mangum import Mangum

from api.routes.analytics import bp as analytics_bp
from api.routes.kpis import bp as kpis_bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(kpis_bp)
    app.register_blueprint(analytics_bp)

    @app.after_request
    def add_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Cache-Control"] = "no-store"
        return response

    return app


app = create_app()
handler = Mangum(WsgiToAsgi(app), lifespan="off")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)