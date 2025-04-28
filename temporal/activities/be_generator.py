# activities/be_generator.py
from temporalio import activity


@activity.defn
async def generate_be_code(be_template: str):
    # Logic giả định: Sinh mã backend từ template
    be_code = f"""
    # Generated BE code from template: {be_template}
    from flask import Flask

    app = Flask(__name__)

    @app.route('/')
    def hello_world():
        return '{be_template} - Backend Generated!'

    if __name__ == '__main__':
        app.run(debug=True)
    """
    return be_code
