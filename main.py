from flask import Flask, render_template, request, jsonify
from flask_codemirror import CodeMirror
from flask_codemirror.fields import CodeMirrorField
from flask_wtf import FlaskForm
from wtforms.fields import SubmitField
import random
import os

app = Flask(__name__)
app.config.from_object(__name__)
with app.app_context():
    app.config['CODEMIRROR_SERVE_TEMPLATES'] = True
    app.config['CODEMIRROR_SERVE_STATIC'] = True
    app.config['CODEMIRROR_LANGUAGES'] = ['python']
    app.config['CODEMIRROR_THEME'] = 'blackboard'
    app.config['SECRET_KEY'] = os.urandom(32)
# Initialize CodeMirror
codemirror = CodeMirror(app)


class CodeForm(FlaskForm):
    code = CodeMirrorField(language='python', config={'lineNumbers': True})
    submit = SubmitField('RUN')


@app.route('/')
def index():
    default_code = '''# Online Python compiler (interpreter) to run Python online.
# Write Python 3 code in this online editor and run it.
print("Try Hello-world")'''
    form = CodeForm()
    form.code.data = default_code
    return render_template('index.html', form=form, output="")

@app.route('/execute', methods=['POST'])
def execute_code():
    form = CodeForm()
    code = request.form.get('code', '')  # Get code from form data
    file_path = "temp_" + f'{random.randrange(1, 10**5):05}' + ".py"  # Unique file name to avoid collisions
    code_file = os.path.join(os.getcwd(), file_path)
    # input = form.code.input 
    #input_data = request.json.get('input_data', '')  # for handling input()


    
    with open(file_path, 'w') as f:
        f.write(code)
        
        

    try:
        # run a docker container using shell command
        os.system(f'docker run --rm -i python:3.9-slim < {file_path} > {file_path}.out 2>&1')
        # Read the output from the file
        with open(file_path + ".out", 'r') as f:
            output = f.read()

        # Clean up by removing the temporary file
        os.remove(file_path)
        
        return jsonify({'output': output, 'exit_code': "exit_code['StatusCode']"})
    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == "__main__":
    app.run(debug=True)
