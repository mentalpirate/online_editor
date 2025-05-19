from flask import Flask, render_template, request, jsonify, session
from flask_codemirror import CodeMirror
from flask_codemirror.fields import CodeMirrorField
from flask_wtf import FlaskForm
from wtforms.fields import SubmitField
from flask_socketio import SocketIO, emit, join_room, leave_room
import eventlet
import eventlet.green.subprocess as subprocess
import random
import os

app = Flask(__name__)
app.config.from_object(__name__)
socketio = SocketIO(app)

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
    default_code = '''# Online Python Interpreter to run Python online.
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



user_procs = {}

@socketio.on('run_code')
def run_code(data):
    code = data.get('code', '')
    sid = request.sid
    rand_id = f'{random.randrange(1, 10**5):05}'
    code_file = f"temp_{rand_id}.py"
    
    with open(code_file, 'w') as f:
        f.write(code)

    cmd = [
        "docker", "run", "--rm", "-i",
        "-v", f"{os.getcwd()}:/code",
        "-w", "/code",
        "python:3.9-slim",
        "python", code_file
    ]
    
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0
    )
    user_procs[sid] = proc

    def read_output():
        try:
            while True:
                output = proc.stdout.read(1)
                if not output:
                    break
                socketio.emit('terminal_output', output.decode('utf-8'), room=sid)
        finally:
            proc.stdout.close()
            os.remove(code_file)
            user_procs.pop(sid, None)
            socketio.emit('terminal_output', '\n==Code Execution Finished==\n', room=sid)

    eventlet.spawn_n(read_output)

@socketio.on('terminal_input')
def on_input(data):
    sid = request.sid
    proc = user_procs.get(sid)
    if proc and proc.stdin:
        try:
            proc.stdin.write(data.encode('utf-8'))
            proc.stdin.flush()
        except Exception as e:
            print(f"Error writing to stdin: {e}")
            socketio.emit('terminal_output', f"\nError: {str(e)}\n", room=sid)


    
    proc.wait()
    # socketio.emit('terminal_output', '\n==Code Execution Finished==\n')       

if __name__ == "__main__":
    socketio.run(app, debug=True)
