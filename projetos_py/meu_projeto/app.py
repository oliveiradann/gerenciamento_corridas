from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import io

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'  # Altere para uma chave secreta segura

# Configurações do banco de dados MySQL
DB_HOST = 'roundhouse.proxy.rlwy.net'
DB_PORT = 56898
DB_USER = 'root'
DB_PASSWORD = 'sxUqOgGEBybKYqMSnURsszVNpzptiZvd'
DB_NAME = 'railway'

# Função para conectar ao banco de dados MySQL
def get_db_connection():
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn

# Inicializa o banco de dados (somente na primeira execução)
def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS corridas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    data DATE NOT NULL,
                    app VARCHAR(50) NOT NULL,
                    distancia FLOAT NOT NULL,
                    valor FLOAT NOT NULL,
                    pagamento VARCHAR(50) NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS custos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    data DATE NOT NULL,
                    tipo VARCHAR(50) NOT NULL,
                    combustivel VARCHAR(50),
                    tipo_especifico VARCHAR(50),
                    valor FLOAT NOT NULL,
                    pagamento VARCHAR(50) NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL,
                    is_admin TINYINT(1) NOT NULL
                )
            ''')
            # Criar o usuário admin com senha "142305" se ele ainda não existir
            hashed_password = generate_password_hash('142305', method='pbkdf2:sha256')
            cursor.execute('''
                INSERT IGNORE INTO users (username, password, is_admin)
                VALUES (%s, %s, %s)
            ''', ('Admin', hashed_password, 1))
            conn.commit()

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Usuário ou senha incorretos!', 'danger')

    return render_template('login.html')

# Rota de logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login'))

# Decorador para proteger rotas que exigem login
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Página inicial (home)
@app.route('/')
@login_required
def home():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT SUM(valor) as total FROM corridas WHERE data = %s', (today,))
        total_valor = cursor.fetchone()['total']
        cursor.execute('SELECT SUM(distancia) as total FROM corridas WHERE data = %s', (today,))
        total_km = cursor.fetchone()['total']
        cursor.execute('SELECT * FROM corridas ORDER BY data DESC')
        corridas = cursor.fetchall()
        cursor.execute('SELECT * FROM custos ORDER BY data DESC')
        custos = cursor.fetchall()
    conn.close()
    
    current_date = datetime.now().strftime('%d/%m/%y')
    return render_template('home.html', total_valor=total_valor or 0, total_km=total_km or 0, corridas=corridas, custos=custos)

# Cadastro de corridas
@app.route('/cadastro', methods=['GET', 'POST'])
@login_required
def cadastro():
    if request.method == 'POST':
        data = request.form['data']
        app_name = request.form['app']
        distancia = request.form['distancia']
        valor = request.form['valor']
        pagamento = request.form['pagamento']
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('INSERT INTO corridas (data, app, distancia, valor, pagamento) VALUES (%s, %s, %s, %s, %s)',
                           (data, app_name, distancia, valor, pagamento))
            conn.commit()
        conn.close()
        return redirect(url_for('home'))

    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('cadastro.html', current_date=current_date)

# Cadastro de custos
@app.route('/cadastro_custos', methods=['GET', 'POST'])
@login_required
def cadastro_custos():
    if request.method == 'POST':
        data = request.form['data']
        tipo = request.form['tipo']
        combustivel = request.form.get('combustivel', '') if tipo == 'Combustível' else ''
        tipo_especifico = request.form.get('tipo_especifico', '') if tipo in ['Manutenção', 'Alimentação'] else ''
        valor = request.form['valor']
        pagamento = request.form['pagamento']
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('INSERT INTO custos (data, tipo, combustivel, tipo_especifico, valor, pagamento) VALUES (%s, %s, %s, %s, %s, %s)',
                           (data, tipo, combustivel, tipo_especifico, valor, pagamento))
            conn.commit()
        conn.close()
        return redirect(url_for('home'))

    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('cadastro_custos.html', current_date=current_date)

# Exclusão de corrida
@app.route('/delete_corrida/<int:id>', methods=['POST'])
@login_required
def delete_corrida(id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('DELETE FROM corridas WHERE id = %s', (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('home'))

# Exclusão de custo
@app.route('/delete_custo/<int:id>', methods=['POST'])
@login_required
def delete_custo(id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('DELETE FROM custos WHERE id = %s', (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('home'))

# Relatório de corridas e custos
@app.route('/relatorio', methods=['GET', 'POST'])
@login_required
def relatorio():
    conn = get_db_connection()

    # Obter a data atual no formato YYYY-MM-DD para campos de entrada de data HTML
    data_atual = datetime.now().strftime('%Y-%m-%d')

    # Inicializar as variáveis com a data atual se não forem definidas pelo usuário
    data_inicio = request.form.get('data_inicio', data_atual)
    data_fim = request.form.get('data_fim', data_atual)

    # Obter os dados filtrados por período
    with conn.cursor() as cursor:
        cursor.execute('SELECT app, COUNT(*) as quantidade, SUM(valor) as total_valor FROM corridas WHERE data BETWEEN %s AND %s GROUP BY app', 
                       (data_inicio, data_fim))
        corridas_por_app = cursor.fetchall()
        cursor.execute('SELECT combustivel, SUM(valor) as total FROM custos WHERE tipo = "Combustível" AND data BETWEEN %s AND %s GROUP BY combustivel', 
                       (data_inicio, data_fim))
        gasto_por_combustivel = cursor.fetchall()
        cursor.execute('SELECT tipo, SUM(valor) as total FROM custos WHERE data BETWEEN %s AND %s GROUP BY tipo', 
                       (data_inicio, data_fim))
        custos_por_tipo = cursor.fetchall()
        cursor.execute('SELECT SUM(valor) as total FROM corridas WHERE data BETWEEN %s AND %s', 
                       (data_inicio, data_fim))
        total_recebido_periodo = cursor.fetchone()
        cursor.execute('SELECT SUM(valor) as total FROM custos WHERE data BETWEEN %s AND %s', 
                       (data_inicio, data_fim))
        total_custos_periodo = cursor.fetchone()

    # Calcular o lucro
    lucro = (total_recebido_periodo['total'] or 0) - (total_custos_periodo['total'] or 0)

    periodo = {"inicio": data_inicio, "fim": data_fim}

    conn.close()

    return render_template('relatorio.html', 
                           dados={
                               "corridas_por_app": corridas_por_app,
                               "gasto_por_combustivel": gasto_por_combustivel,
                               "custos_por_tipo": custos_por_tipo,
                               "total_recebido_periodo": total_recebido_periodo['total'] if total_recebido_periodo else 0,
                               "total_custos": total_custos_periodo['total'] if total_custos_periodo else 0,
                               "lucro": lucro
                           },
                           periodo=periodo,
                           data_inicio=data_inicio,
                           data_fim=data_fim)

# Download do relatório
@app.route('/download_relatorio', methods=['GET'])
@login_required
def download_relatorio():
    conn = get_db_connection()

    # Capturar as datas de início e fim dos parâmetros de consulta (query parameters)
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    # Verificar se as datas foram fornecidas, caso contrário usar a data atual
    if not data_inicio or not data_fim:
        data_atual = datetime.now().strftime('%Y-%m-%d')
        data_inicio = data_fim = data_atual

    # Obter os dados filtrados por período
    with conn.cursor() as cursor:
        cursor.execute('SELECT app, COUNT(*) as quantidade, SUM(valor) as total_valor FROM corridas WHERE data BETWEEN %s AND %s GROUP BY app ORDER BY total_valor DESC', 
                       (data_inicio, data_fim))
        corridas_por_app = cursor.fetchall()
        cursor.execute('SELECT combustivel, SUM(valor) as total FROM custos WHERE tipo = "Combustível" AND data BETWEEN %s AND %s GROUP BY combustivel ORDER BY total DESC', 
                       (data_inicio, data_fim))
        gasto_por_combustivel = cursor.fetchall()
        cursor.execute('SELECT tipo, SUM(valor) as total FROM custos WHERE data BETWEEN %s AND %s GROUP BY tipo ORDER BY total DESC', 
                       (data_inicio, data_fim))
        custos_por_tipo = cursor.fetchall()
        cursor.execute('SELECT SUM(valor) as total FROM corridas WHERE data BETWEEN %s AND %s', 
                       (data_inicio, data_fim))
        total_recebido_periodo = cursor.fetchone()
        cursor.execute('SELECT SUM(valor) as total FROM custos WHERE data BETWEEN %s AND %s', 
                       (data_inicio, data_fim))
        total_custos_periodo = cursor.fetchone()

    # Calcular lucro
    lucro = (total_recebido_periodo['total'] or 0) - (total_custos_periodo['total'] or 0)

    # Criar o conteúdo do relatório
    relatorio = io.StringIO()
    relatorio.write('Relatório de Corridas e Custos\n')
    relatorio.write('============================\n\n')
    relatorio.write(f'Período: {data_inicio} até {data_fim}\n\n')

    # Adicionar informações sobre Corridas
    relatorio.write('Corridas por Aplicativo:\n')
    for corrida in corridas_por_app:
        relatorio.write(f'- {corrida["app"]}: {corrida["quantidade"]} corridas, R$ {corrida["total_valor"]:.2f}\n')
    
    # Adicionar informações sobre Combustível
    relatorio.write('\nGastos por Tipo de Combustível:\n')
    for combustivel in gasto_por_combustivel:
        relatorio.write(f'- {combustivel["combustivel"]}: R$ {combustivel["total"]:.2f}\n')

    # Adicionar informações sobre Custos
    relatorio.write('\nGastos por Tipo de Custo:\n')
    for custo in custos_por_tipo:
        relatorio.write(f'- {custo["tipo"]}: R$ {custo["total"]:.2f}\n')

    # Adicionar resumo financeiro
    relatorio.write('\nResumo Financeiro:\n')
    relatorio.write(f'Ganho Bruto: R$ {total_recebido_periodo["total"]:.2f}\n')
    relatorio.write(f'Custos Totais: R$ {total_custos_periodo["total"]:.2f}\n')
    relatorio.write(f'Lucro: R$ {lucro:.2f}\n')

    # Preparar para o download
    relatorio.seek(0)
    return send_file(
        io.BytesIO(relatorio.getvalue().encode()),
        mimetype='text/plain',
        as_attachment=True,
        download_name='relatorio.txt'
    )

# Cadastro de usuários
@app.route('/cadastro_usuario', methods=['GET', 'POST'])
@login_required
def cadastro_usuario():
    if not session.get('is_admin'):
        flash('Acesso negado: você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin = int(request.form.get('is_admin', 0))
        conn = get_db_connection()
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            with conn.cursor() as cursor:
                cursor.execute('INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)', 
                               (username, hashed_password, is_admin))
                conn.commit()
            flash('Usuário cadastrado com sucesso!', 'success')
        except pymysql.IntegrityError:
            flash('Erro: Nome de usuário já existe.', 'danger')

        conn.close()
        return redirect(url_for('cadastro_usuario'))

    return render_template('cadastro_usuario.html')

if __name__ == '__main__':
    init_db()  # Inicializa o banco de dados na primeira execução
    app.run(debug=True)