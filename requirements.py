import sys
import subprocess
import codecs


with codecs.open('requirements.txt', 'r', 'utf-8') as f:
    for inst in f.readlines():
        print(f'\n\nInstalling: {inst}\n\n')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', inst.strip()])

input('\n\nDone.')
