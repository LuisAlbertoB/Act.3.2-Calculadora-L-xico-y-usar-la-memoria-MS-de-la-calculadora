from flask import Flask, render_template, request
import re
from collections import namedtuple

app = Flask(__name__)

# Definición de la estructura del Token
Token = namedtuple('Token', ['tipo', 'valor'])

# Definición de los tipos de tokens y sus expresiones regulares
TOKENS = [
    ('NUMERO', r'\d+'),  # Números enteros
    ('OPERADOR', r'[+\-*/]'),  # Operadores aritméticos
    ('LPAREN', r'\('),  # Paréntesis izquierdo
    ('RPAREN', r'\)'),  # Paréntesis derecho
    ('ESPACIO', r'\s+'),  # Espacios en blanco (a ignorar)
]

# Compilación de las expresiones regulares
TOKEN_REGEX = '|'.join('(?P<%s>%s)' % pair for pair in TOKENS)
MASTER_PATTERN = re.compile(TOKEN_REGEX)


def lexer(text):
    tokens = []
    for mo in MASTER_PATTERN.finditer(text):
        tipo = mo.lastgroup
        valor = mo.group()
        if tipo != 'ESPACIO':  # Ignorar espacios en blanco
            tokens.append(Token(tipo, valor))
    return tokens


def contar_tokens(tokens):
    total = len(tokens)
    numeros = sum(1 for token in tokens if token.tipo == 'NUMERO')
    operadores = sum(1 for token in tokens if token.tipo == 'OPERADOR')
    return total, numeros, operadores


class Nodo:
    def __init__(self, valor):
        self.valor = valor
        self.izquierda = None
        self.derecha = None

    def to_dict(self):
        node = {'name': self.valor}
        if self.izquierda:
            node['children'] = [self.izquierda.to_dict()]
        if self.derecha:
            if 'children' in node:
                node['children'].append(self.derecha.to_dict())
            else:
                node['children'] = [self.derecha.to_dict()]
        return node


def shunting_yard(tokens):
    salida = []
    operadores = []
    precedencia = {'+': 1, '-': 1, '*': 2, '/': 2}

    for token in tokens:
        if token.tipo == 'NUMERO':
            salida.append(token)
        elif token.tipo == 'OPERADOR':
            while (operadores and operadores[-1].tipo == 'OPERADOR' and
                   precedencia[operadores[-1].valor] >= precedencia[token.valor]):
                salida.append(operadores.pop())
            operadores.append(token)
        elif token.tipo == 'LPAREN':
            operadores.append(token)
        elif token.tipo == 'RPAREN':
            while operadores and operadores[-1].tipo != 'LPAREN':
                salida.append(operadores.pop())
            operadores.pop()  # Eliminar el '(' de la pila
    while operadores:
        salida.append(operadores.pop())
    return salida


def construir_arbol(rpn_tokens):
    stack = []
    for token in rpn_tokens:
        if token.tipo == 'NUMERO':
            stack.append(Nodo(token.valor))
        elif token.tipo == 'OPERADOR':
            nodo = Nodo(token.valor)
            nodo.derecha = stack.pop()
            nodo.izquierda = stack.pop()
            stack.append(nodo)
    return stack[0] if stack else None


def evaluar_rpn(rpn_tokens):
    stack = []
    for token in rpn_tokens:
        if token.tipo == 'NUMERO':
            stack.append(int(token.valor))
        elif token.tipo == 'OPERADOR':
            b = stack.pop()
            a = stack.pop()
            if token.valor == '+':
                stack.append(a + b)
            elif token.valor == '-':
                stack.append(a - b)
            elif token.valor == '*':
                stack.append(a * b)
            elif token.valor == '/':
                stack.append(a / b)
    return stack[0] if stack else None


# Variable global para almacenar la memoria (MS)
memoria_global = {'MS': None}


@app.route('/', methods=['GET', 'POST'])
def index():
    expresion = ''
    resultado = None
    tokens = []
    total_tokens = 0
    total_numeros = 0
    total_operadores = 0
    rpn = []
    arbol = None
    arbol_dict = {}
    mensaje_error = ''

    if request.method == 'POST':
        if 'accion' in request.form:
            accion = request.form['accion']
            expresion = request.form.get('expresion', '')
            if accion == 'Ingresar':
                valor = request.form.get('valor', '')
                expresion += valor
            elif accion == 'Borrar':
                expresion = borrar_ultimo_numero(expresion)
            elif accion == 'Limpiar':
                expresion = ''
            elif accion == 'Memoria':
                if memoria_global['MS'] is not None:
                    expresion += str(memoria_global['MS'])
                else:
                    mensaje_error = 'No hay valor almacenado en memoria (MS).'
            elif accion == 'Calcular':
                # Reemplazar 'MS' por el valor almacenado en memoria
                if 'MS' in expresion:
                    if memoria_global['MS'] is not None:
                        expresion = expresion.replace('MS', str(memoria_global['MS']))
                    else:
                        mensaje_error = 'No hay valor almacenado en memoria (MS).'
                # Analizar y calcular la expresión
                try:
                    tokens = lexer(expresion)
                    total_tokens, total_numeros, total_operadores = contar_tokens(tokens)
                    rpn = shunting_yard(tokens)
                    arbol = construir_arbol(rpn)
                    resultado = evaluar_rpn(rpn)
                    # Almacenar el resultado en memoria
                    memoria_global['MS'] = resultado
                    if arbol:
                        arbol_dict = arbol.to_dict()
                except Exception as e:
                    mensaje_error = f'Error al calcular la expresión: {e}'

    return render_template('index.html',
                           expresion=expresion,
                           resultado=resultado,
                           tokens=tokens,
                           total_tokens=total_tokens,
                           total_numeros=total_numeros,
                           total_operadores=total_operadores,
                           rpn=rpn,
                           arbol=arbol_dict,
                           mensaje_error=mensaje_error,
                           memoria=memoria_global['MS'])


def borrar_ultimo_numero(expresion):
    i = len(expresion) - 1
    while i >= 0 and expresion[i].isdigit():
        i -= 1
    return expresion[:i + 1]


if __name__ == '__main__':
    app.run()