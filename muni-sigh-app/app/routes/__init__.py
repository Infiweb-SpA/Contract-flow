from app.routes.dashboard import dashboard_bp
from app.routes.contract_builder import contract_builder_bp
from app.routes.decrees import decrees_bp
from app.routes.admin import admin_bp

def register_routes(app):
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(contract_builder_bp)
    app.register_blueprint(decrees_bp)
    app.register_blueprint(admin_bp)