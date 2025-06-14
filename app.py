import requests
from flask import Flask, request, jsonify
from base64 import b64encode
import os

app = Flask(__name__)

# === CONFIGURAÇÕES ZENDESK ===
ZENDESK_SUBDOMINIO = 'conbcrcxfabio1745583316'
ZENDESK_EMAIL = 'consultoriazendesk@bcrcx.com/token'
ZENDESK_TOKEN = 'RJ2akwbMSs0BBZMqKy3j6l3ALWh00j3Dj9vgHmcv'
CAMPO_CUSTOM_POKEMON = 'custom_fields_37991201870491'  # ID do campo personalizado (dropdown de pokémons)

# === AUTENTICAÇÃO ZENDESK ===
def get_auth_header():
    auth = b64encode(f"{ZENDESK_EMAIL}:{ZENDESK_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }

# === BUSCAR DADOS DA POKEAPI ===
def buscar_dados_pokemon(nome):
    url = f'https://pokeapi.co/api/v2/pokemon/{nome.lower()}'
    res = requests.get(url)

    if res.status_code != 200:
        return None

    dados = res.json()
    return {
        "nome": dados['name'],
        "tipos": ', '.join(t['type']['name'] for t in dados['types']),
        "imagem": dados['sprites']['front_default']
    }

# === ATUALIZAR COMENTÁRIO DO TICKET ZENDESK ===
def atualizar_ticket(ticket_id, pokemon):
    dados = buscar_dados_pokemon(pokemon)
    if not dados:
        return False

    html_body = (
        f"<p><strong>Nome:</strong> {dados['nome'].capitalize()}</p>"
        f"<p><strong>Tipo(s):</strong> {dados['tipos']}</p>"
        f"<p><img src='{dados['imagem']}' alt='{dados['nome']}' /></p>"
    )

    payload = {
        "ticket": {
            "comment": {
                "html_body": html_body,
                "public": True
            },
            "tags": ["-teste_pokeapi"]  # Remove a tag após o update
        }
    }

    url = f"https://{ZENDESK_SUBDOMINIO}.zendesk.com/api/v2/tickets/{ticket_id}.json"
    res = requests.put(url, headers=get_auth_header(), json=payload)
    return res.status_code in [200, 201]

# === ENDPOINT DO WEBHOOK ===
@app.route('/webhook-pokeapi', methods=['POST'])
def receber_webhook():
    data = request.json

    ticket = data.get('ticket_event', {}).get('ticket', {})
    ticket_id = ticket.get('id')
    campos_customizados = ticket.get('custom_fields', [])

    pokemon = None
    for campo in campos_customizados:
        if campo.get('id') == int(CAMPO_CUSTOM_POKEMON.replace('custom_fields_', '')):
            pokemon = campo.get('value')
            break

    if not ticket_id or not pokemon:
        return jsonify({"error": "ID do ticket ou pokémon não encontrado"}), 400

    sucesso = atualizar_ticket(ticket_id, pokemon)
    return jsonify({"status": "sucesso" if sucesso else "erro ao atualizar o ticket"})

# === EXECUÇÃO DO APP FLASK ===
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
