from app import create_app, Config # db # Akan diaktifkan nanti
# from app.models import User, Detection # Akan diaktifkan nanti

app = create_app()

# @app.shell_context_processor
# def make_shell_context():
#     return {'db': db, 'User': User, 'Detection': Detection} # Akan diaktifkan nanti

if __name__ == '__main__':
    app.run(debug=True) # debug=True hanya untuk pengembangan