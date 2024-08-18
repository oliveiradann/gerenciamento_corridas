import os

# Define a estrutura do projeto
project_name = "meu_projeto"
folders = ["templates"]
files = {
    "app.py": """from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('test.html')

if __name__ == '__main__':
    app.run(debug=True)
""",
    "templates/test.html": """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Página de Teste</title>
</head>
<body>
    <h1>Testando o Template</h1>
    <p>Se você está vendo esta mensagem, o Flask está funcionando corretamente.</p>
</body>
</html>
"""
}

# Cria a pasta principal do projeto
if not os.path.exists(project_name):
    os.makedirs(project_name)

# Cria as pastas do projeto
for folder in folders:
    folder_path = os.path.join(project_name, folder)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

# Cria os arquivos do projeto
for file_path, file_content in files.items():
    full_path = os.path.join(project_name, file_path)
    with open(full_path, "w") as file:
        file.write(file_content)

print(f"Estrutura do projeto '{project_name}' criada com sucesso!")
