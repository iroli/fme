import sys
import subprocess


print('\n\nInstalling python3-venv (Debian-like systems only as of now; sudo required):\n\n')
# noinspection PyBroadException
try:
    subprocess.check_call(['sudo', 'apt', 'install', 'python3-venv'])
except:
    pass


venv_name = 'enc_env'

print(f'\n\nCreating virtual environment with name: {venv_name}\n\n')
subprocess.check_call([sys.executable, '-m', 'venv', venv_name])


input('\n\nDone.\n\n'
      'If you\'re working in an IDE please configure environment (interpreter) there and run requirements.py\n\n'
      'If you\'re working from terminal / command line / powershell,\n'
      'please run following commands to activate the environment, then run requirements.py:\n\n'
      'For Windows:\n'
      f'.\\{venv_name}\\Scripts\\activate\n\n'
      'For Linux / MacOS:\n'
      f'source {venv_name}/bin/activate\n\n')
